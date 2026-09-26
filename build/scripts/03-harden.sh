#!/usr/bin/env bash
# Stage 3: Security Lockdown & Resource Hardening (docs/BUILD_SYSTEM.md §3 /
# docs/ANTI_CHEAT_AND_SECURITY.md).
#
# Bakes a static Zero-Trust security posture into $ROOTFS at build time:
#   - nftables IPv4-only default-DROP firewall with judge/DNS/NTP whitelisting
#   - Network-wide IPv6 disablement (sysctl)
#   - USB mass-storage lockdown (modern JavaScript Polkit rules + Udev fallback)
#   - EarlyOOM resource guard configured with -n D-Bus broadcast
#   - TTY/VT switching lockdown (logind NAutoVTs=1, autovt masked, stripped keymap)
#   - Contestant privilege hardening (sudo purge, locked root account)
#
# NOTE: Real per-event dynamic firewall rendering, mode transitions, and
# live DNS resolution from gallos.toml are Phase 3 (gallos-daemon) work.
#
# NOTE: The following items are explicitly deferred to later phases:
#   - earlyoom --avoid/--prefer regexes and oom_score_adj overrides for
#     gallos-daemon, labwc, and browsers (deferred to Phase 3/4 when those exist)
#   - mDNS, CUPS printing, and ICMP venue-controller rules in nftables
#     (deferred to Phase 4 when printing and venue subsystems are introduced)
#   - Dynamic USB re-authorization at contest end (deferred to Phase 3)
set -euo pipefail

CONFIG="$1"
ROOTFS="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=build/scripts/lib-chroot.sh
source "$SCRIPT_DIR/lib-chroot.sh"

disable_ipv6="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" security.disable_ipv6)"
mapfile -t judge_ips < <(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" security.judge_ips)
venue_controller_ip="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" security.venue_controller_ip)"
local_dns_ip="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" security.local_dns_ip)"
mapfile -t telemetry_dns_blacklist < <(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" security.telemetry_dns_blacklist)
mapfile -t blocked_tcp_ports < <(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" security.blocked_tcp_ports)
allow_usb_storage="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" security.allow_usb_storage)"

chroot_mount "$ROOTFS"
# Deliberately not unmounted here: 04-optimize.sh chroots into the same
# rootfs next within the same container run. chroot_umount runs once, at
# the end of 04-optimize.sh, after every chroot-dependent stage is done.

echo "Installing security packages (nftables, earlyoom, kbd)..."
chroot "$ROOTFS" /bin/bash -euxc "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        nftables \
        kbd \
        earlyoom
"

echo "Configuring nftables firewall..."
judge_elements=""
if [[ ${#judge_ips[@]} -gt 0 ]]; then
    judge_elements="$(IFS=, ; echo "${judge_ips[*]}")"
fi

venue_elements="${venue_controller_ip:-192.168.50.1}"

telemetry_elements=""
if [[ ${#telemetry_dns_blacklist[@]} -gt 0 ]]; then
    telemetry_elements="$(IFS=, ; echo "${telemetry_dns_blacklist[*]}")"
fi

blocked_ports_str="22, 853"
if [[ ${#blocked_tcp_ports[@]} -gt 0 ]]; then
    blocked_ports_str="$(IFS=, ; echo "${blocked_tcp_ports[*]}")"
fi

dns_ip="${local_dns_ip:-192.168.1.1}"

cat > "$ROOTFS/etc/nftables.conf" <<EOF
#!/usr/sbin/nft -f

flush ruleset

table ip gallos_filter {
    set allowed_judge_ips {
        type ipv4_addr
        flags interval
        elements = { ${judge_elements} }
    }

    set allowed_venue_controller_ip {
        type ipv4_addr
        elements = { ${venue_elements} }
    }

    set telemetry_dns_blacklist {
        type ipv4_addr
        elements = { ${telemetry_elements} }
    }

    chain output {
        type filter hook output priority 0; policy drop;

        # 1. Allow Loopback (Required for local debuggers and local servers)
        oif "lo" accept

        # 2. Allow Established / Related connections
        ct state established,related accept

        # 3. Allow outbound DHCP client negotiation (discover/request). This
        # must be explicit: conntrack does not reliably track the broadcast
        # DHCP handshake as an established/related pseudo-connection, and
        # without it a DHCP-addressed machine can never acquire an IP at all
        # under a default-drop policy (chicken-and-egg — no address yet
        # means no venue_controller_ip/judge_ips to scope any other rule to).
        udp sport 68 udp dport 67 accept

        # 4. Hard-Drop Telemetry DNS & Blocked Ports (e.g. SSH 22, DoT 853)
        ip daddr @telemetry_dns_blacklist drop
        tcp dport { ${blocked_ports_str} } drop

        # 5. Allow Local DNS (Port 53 UDP/TCP) to verified local gateway only
        udp dport 53 ip daddr ${dns_ip} accept
        tcp dport 53 ip daddr ${dns_ip} accept

        # 6. Allow NTP Time Synchronization (Port 123) scoped to Venue Controller
        udp dport 123 ip daddr @allowed_venue_controller_ip accept

        # 7. Allow HTTP/HTTPS exclusively to Whitelisted Judge IPs
        tcp dport { 80, 443 } ip daddr @allowed_judge_ips accept

        # 8. Venue Controller audit/telemetry upload (HTTPS)
        tcp dport 443 ip daddr @allowed_venue_controller_ip accept

        # 9. Rate-limited Audit Logging for Denied Outbound Attempts
        limit rate 5/minute burst 7 packets log prefix "GALLOS_DENIED: " flags all

        # 10. Reject everything else with immediate ICMP port unreachable
        reject
    }

    chain input {
        type filter hook input priority 0; policy drop;
        iif "lo" accept
        ct state established,related accept
        # DHCP server reply (offer/ack) — same conntrack caveat as the
        # outbound rule above; the broadcast reply isn't reliably matched
        # as established/related, so it needs an explicit allow.
        udp sport 67 udp dport 68 accept
    }
}
EOF
chmod 0644 "$ROOTFS/etc/nftables.conf"
chroot "$ROOTFS" systemctl enable nftables.service

if [[ "$disable_ipv6" == "true" ]]; then
    echo "Disabling IPv6 via sysctl fallback..."
    cat > "$ROOTFS/etc/sysctl.d/99-gallos-noipv6.conf" <<'EOF'
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
EOF
fi

echo "Configuring peripheral & USB lockdown..."
mkdir -p "$ROOTFS/etc/polkit-1/rules.d"
if [[ "$allow_usb_storage" == "false" ]]; then
    install -m 0644 \
        "$REPO_ROOT/vendor/inherited/maratona-usuario-icpc/99-gallos-usb-block.rules" \
        "$ROOTFS/etc/polkit-1/rules.d/99-gallos-usb-block.rules"
fi

mkdir -p "$ROOTFS/etc/udev/rules.d"
cat > "$ROOTFS/etc/udev/rules.d/99-contest-usb-block.rules" <<'EOF'
# GallosOS fallback USB mass storage block rule.
# Must match on the usb_device node (DEVTYPE), not a usb_interface node:
# the "authorized" sysfs attribute this rule writes only exists on the
# device node, while "bInterfaceClass" is only set on its interface
# children — hence ATTRS{} (plural, searches descendants) instead of
# ATTR{} (which would only see the matched node's own attributes and, on
# an interface node, has no "authorized" file to write).
ACTION=="add", SUBSYSTEM=="usb", DEVTYPE=="usb_device", ATTRS{bInterfaceClass}=="08", ATTR{authorized}="0"
EOF

echo "Configuring EarlyOOM..."
cat > "$ROOTFS/etc/default/earlyoom" <<'EOF'
EARLYOOM_ARGS="-r 60 -m 10 -s 5 -n --avoid '^(gallos-daemon|labwc|mako|Xwayland)$' --prefer '^(chromium|firefox|code)$'"
EOF
chroot "$ROOTFS" systemctl enable earlyoom.service
chroot "$ROOTFS" systemctl enable seatd.service || true

echo "Hardening virtual terminal switching (TTY lockdown)..."
mkdir -p "$ROOTFS/etc/systemd/logind.conf.d"
cat > "$ROOTFS/etc/systemd/logind.conf.d/99-gallos-novt.conf" <<'EOF'
[Login]
NAutoVTs=1
ReserveVT=0
EOF

chroot "$ROOTFS" systemctl mask autovt@.service

mkdir -p "$ROOTFS/etc/gallos"
if compgen -G "$ROOTFS/etc/console-setup/cached_*.kmap.gz" >/dev/null && zcat "$ROOTFS"/etc/console-setup/cached_*.kmap.gz >/dev/null 2>&1; then
    zcat "$ROOTFS"/etc/console-setup/cached_*.kmap.gz | sed -E 's/Console_([2-9]|[1-9][0-9]+)/VoidSymbol/g' > "$ROOTFS/etc/gallos/novt-noswitch.map"
elif chroot "$ROOTFS" dumpkeys >/dev/null 2>&1; then
    chroot "$ROOTFS" dumpkeys | sed -E 's/Console_([2-9]|[1-9][0-9]+)/VoidSymbol/g' > "$ROOTFS/etc/gallos/novt-noswitch.map"
else
    cat > "$ROOTFS/etc/gallos/novt-noswitch.map" <<'EOF'
# Disable VT switching keycodes
control alt keycode 59 = VoidSymbol
control alt keycode 60 = VoidSymbol
control alt keycode 61 = VoidSymbol
control alt keycode 62 = VoidSymbol
control alt keycode 63 = VoidSymbol
control alt keycode 64 = VoidSymbol
control alt keycode 65 = VoidSymbol
control alt keycode 66 = VoidSymbol
control alt keycode 67 = VoidSymbol
control alt keycode 68 = VoidSymbol
control alt keycode 87 = VoidSymbol
control alt keycode 88 = VoidSymbol
alt keycode 59 = VoidSymbol
alt keycode 60 = VoidSymbol
alt keycode 61 = VoidSymbol
alt keycode 62 = VoidSymbol
alt keycode 63 = VoidSymbol
alt keycode 64 = VoidSymbol
alt keycode 65 = VoidSymbol
alt keycode 66 = VoidSymbol
alt keycode 67 = VoidSymbol
alt keycode 68 = VoidSymbol
alt keycode 87 = VoidSymbol
alt keycode 88 = VoidSymbol
EOF
fi

cat > "$ROOTFS/etc/systemd/system/gallos-novt-keymap.service" <<'EOF'
[Unit]
Description=Disable Console Switching Keymap
DefaultDependencies=no
After=systemd-udev-settle.service
Before=getty.target shutdown.target

[Service]
Type=oneshot
ExecStart=/usr/bin/loadkeys /etc/gallos/novt-noswitch.map
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

chroot "$ROOTFS" systemctl enable gallos-novt-keymap.service

echo "Closing serial-console autologin bypass..."
# 02-provision.sh installs passwordless autologin as 'contestant' on BOTH
# tty1 (graphical-console walking-skeleton convenience) and ttyS0 (headless
# QEMU serial-console verification convenience) — see its comment: "NOT
# production/anti-cheat-safe... Phase 2 locks this down." The VT-switch
# lockdown above only blocks lateral movement between virtual terminals
# from an already-open session; it does nothing about ttyS0, which is a
# wholly separate mechanism reachable by anyone with physical/BMC serial
# access. contestant has no password set, so once this drop-in is gone
# the serial console has no way to authenticate in at all. tty1's
# autologin is left as-is: it's the still-missing Wayland kiosk's landing
# spot (Phase 3) and was explicitly out of scope for this pass.
rm -rf "$ROOTFS/etc/systemd/system/serial-getty@ttyS0.service.d"

echo "Hardening contestant privileges (sudo binary purge & root lock)..."
# In Ubuntu 24.04, the casper package declares an explicit 'Depends: sudo'.
# Running 'apt-get purge sudo' would cascade-remove casper and break live boot.
# As defense-in-depth, purge the setuid binaries and configuration directly,
# ensuring 'sudo' cannot be found or executed by contestant, and lock root.
chroot "$ROOTFS" /bin/bash -euxc "
    rm -f /usr/bin/sudo /usr/bin/sudoedit /usr/sbin/visudo
    rm -rf /etc/sudoers /etc/sudoers.d
    passwd -l root || true
"

echo "Installing and enabling gallos-daemon.service..."
# gallos-daemon.service's ProtectSystem=strict + ReadWritePaths= requires
# every listed path to already exist at service start — systemd bind-mounts
# each one back to read-write over the otherwise read-only root, which
# fails outright (226/NAMESPACE) for a path that isn't there yet. Chromium/
# Firefox aren't installed on every profile (this walking-skeleton one
# installs neither), so their directories must be pre-created or the daemon
# crash-loops on every single boot of a profile lacking a browser.
mkdir -p "$ROOTFS/etc/chromium/policies/managed" "$ROOTFS/etc/firefox/policies" "$ROOTFS/media/event-data"
install -m 0644 "$REPO_ROOT/daemon/gallos-daemon.service" "$ROOTFS/etc/systemd/system/gallos-daemon.service"
install -m 0644 "$REPO_ROOT/daemon/gallos-event-storage.service" "$ROOTFS/etc/systemd/system/gallos-event-storage.service"
install -m 0644 "$REPO_ROOT/daemon/gallos-root-access.service" "$ROOTFS/etc/systemd/system/gallos-root-access.service"
install -m 0644 "$REPO_ROOT/daemon/gallos-recovery-console.service" "$ROOTFS/etc/systemd/system/gallos-recovery-console.service"
chroot "$ROOTFS" systemctl enable gallos-daemon.service

echo "Stage 3 complete."
