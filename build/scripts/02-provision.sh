#!/usr/bin/env bash
# Provisioning stage: installs kernel, casper live-boot hooks, base utilities,
# and the Wayland kiosk desktop environment (labwc, waybar, foot, mako, swaybg).
set -euo pipefail

CONFIG="$1"
ROOTFS="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=build/scripts/lib-chroot.sh
source "$SCRIPT_DIR/lib-chroot.sh"

kernel_pkg="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" build.kernel)"
mapfile -t extra_pkgs < <(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" packages.preinstall_apt)

chroot_mount "$ROOTFS"

# 1. Install packages inside chroot
chroot "$ROOTFS" /bin/bash -euxc "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends --fix-missing \
        '$kernel_pkg' \
        casper \
        initramfs-tools \
        systemd-sysv \
        network-manager \
        locales \
        plymouth \
        plymouth-theme-ubuntu-text \
        zstd \
        fonts-font-awesome \
        ${extra_pkgs[*]@Q}

    echo 'gallos-live' > /etc/hostname
    { echo overlay; echo squashfs; echo isofs; echo vfat; echo exfat; } >> /etc/initramfs-tools/modules

    # Create contestant user with video/input/render permissions
    useradd -m -s /bin/bash contestant || true
    usermod -a -G video,input,render contestant || true
    if getent group _seatd >/dev/null 2>&1; then
        usermod -a -G _seatd contestant || true
    fi
"

# 2. System-wide dotfiles for Wayland Kiosk (/etc/xdg/)
mkdir -p "$ROOTFS/etc/xdg/labwc" "$ROOTFS/etc/xdg/waybar" "$ROOTFS/etc/xdg/foot" "$ROOTFS/etc/xdg/mako" "$ROOTFS/usr/share/backgrounds/gallos"

# Labwc window management & keybindings
cat > "$ROOTFS/etc/xdg/labwc/rc.xml" <<'EOF'
<?xml version="1.0"?>
<labwc_config>
  <core>
    <decoration>server</decoration>
    <gap>0</gap>
  </core>
  <theme>
    <name>Adwaita</name>
    <cornerRadius>4</cornerRadius>
  </theme>
  <keyboard>
    <keybind key="W-Return">
      <action name="Execute" command="foot" />
    </keybind>
    <keybind key="W-space">
      <action name="Execute" command="gallos-layout-toggle" />
    </keybind>
    <keybind key="A-Shift_L">
      <action name="Execute" command="gallos-layout-toggle" />
    </keybind>
    <keybind key="A-Tab">
      <action name="NextWindow" />
    </keybind>
    <keybind key="A-F4">
      <action name="Close" />
    </keybind>
    <keybind key="W-q">
      <action name="Close" />
    </keybind>
    <keybind key="W-d">
      <action name="Execute" command="wmenu-run" />
    </keybind>
  </keyboard>
  <mouse>
    <default />
  </mouse>
</labwc_config>
EOF

# Labwc autostart
cat > "$ROOTFS/etc/xdg/labwc/autostart" <<'EOF'
#!/bin/sh
swaybg -i /usr/share/backgrounds/gallos/default.png -m fill &
mako -c /etc/xdg/mako/config &
waybar -c /etc/xdg/waybar/config.jsonc -s /etc/xdg/waybar/style.css &
EOF
chmod +x "$ROOTFS/etc/xdg/labwc/autostart"

# Labwc environment
cat > "$ROOTFS/etc/xdg/labwc/environment" <<'EOF'
XDG_CURRENT_DESKTOP=labwc
MOZ_ENABLE_WAYLAND=1
QT_QPA_PLATFORM=wayland
GDK_BACKEND=wayland
_JAVA_AWT_WM_NONREPARENTING=1
EOF

# Waybar status bar configuration
cat > "$ROOTFS/etc/xdg/waybar/config.jsonc" <<'EOF'
{
    "layer": "top",
    "position": "top",
    "height": 32,
    "modules-left": ["custom/appmenu", "wlr/taskbar"],
    "modules-center": ["custom/contest_badge", "custom/countdown"],
    "modules-right": ["network", "clock"],
    "custom/appmenu": {
        "format": " 🏆 GallosOS ",
        "tooltip": false,
        "on-click": "wmenu-run"
    },
    "wlr/taskbar": {
        "format": "{icon} {title}",
        "on-click": "activate",
        "icon-size": 16
    },
    "custom/contest_badge": {
        "format": "MODE: DEFAULT",
        "tooltip": false
    },
    "custom/countdown": {
        "format": "⏳ Standby",
        "tooltip": false
    },
    "network": {
        "format-wifi": " {essid} ({signalStrength}%)",
        "format-ethernet": " {ipaddr}",
        "format-disconnected": " Offline",
        "tooltip-format": "{ifname}: {ipaddr}"
    },
    "clock": {
        "format": " {:%H:%M}",
        "tooltip-format": "{:%Y-%m-%d %A}"
    }
}
EOF

# Waybar styling
cat > "$ROOTFS/etc/xdg/waybar/style.css" <<'EOF'
* {
    border: none;
    border-radius: 0;
    /* Font Awesome provides icon glyphs; Liberation/DejaVu provide text. */
    font-family: "Font Awesome 6 Free", "Font Awesome 6 Free Solid",
                 "Liberation Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
    min-height: 0;
}

window#waybar {
    background: #1e1e2e;
    color: #cdd6f4;
    border-bottom: 2px solid #313244;
}

#custom-appmenu {
    background: #89b4fa;
    color: #11111b;
    font-weight: bold;
    padding: 0 12px;
    margin-right: 8px;
}

#custom-contest_badge {
    background: #a6e3a1;
    color: #11111b;
    font-weight: bold;
    padding: 0 10px;
    border-radius: 3px;
    margin: 4px;
}

#custom-countdown {
    background: #313244;
    color: #f9e2af;
    padding: 0 10px;
    margin: 4px;
    border-radius: 3px;
}

#clock, #network {
    padding: 0 10px;
    color: #cdd6f4;
}
EOF

# Foot terminal configuration
cat > "$ROOTFS/etc/xdg/foot/foot.ini" <<'EOF'
[main]
font=Liberation Mono:size=11,DejaVu Sans Mono:size=11
pad=6x6

[colors]
alpha=0.95
background=1e1e2e
foreground=cdd6f4

regular0=45475a
regular1=f38ba8
regular2=a6e3a1
regular3=f9e2af
regular4=89b4fa
regular5=f5c2e7
regular6=94e2d5
regular7=bac2de

bright0=585b70
bright1=f38ba8
bright2=a6e3a1
bright3=f9e2af
bright4=89b4fa
bright5=f5c2e7
bright6=94e2d5
bright7=a6adc8
EOF

# Mako notification configuration
cat > "$ROOTFS/etc/xdg/mako/config" <<'EOF'
font=Liberation Sans 11
background-color=#1e1e2ecc
text-color=#cdd6f4
border-color=#89b4fa
border-size=2
border-radius=4
default-timeout=5000
anchor=bottom-right
margin=12
padding=10
EOF

# Keyboard layout switcher helper
cat > "$ROOTFS/usr/bin/gallos-layout-toggle" <<'EOF'
#!/bin/bash
LAYOUT_FILE="/tmp/gallos_layout"
LAYOUTS=("us" "latam" "es" "br")
CURRENT="us"
[ -f "$LAYOUT_FILE" ] && CURRENT="$(cat "$LAYOUT_FILE")"

NEXT="us"
for i in "${!LAYOUTS[@]}"; do
    if [ "${LAYOUTS[$i]}" = "$CURRENT" ]; then
        NEXT_IDX=$(( (i + 1) % ${#LAYOUTS[@]} ))
        NEXT="${LAYOUTS[$NEXT_IDX]}"
        break
    fi
done

echo "$NEXT" > "$LAYOUT_FILE"
notify-send -t 1500 "Keyboard Layout" "Active layout: $NEXT" 2>/dev/null || true
EOF
chmod +x "$ROOTFS/usr/bin/gallos-layout-toggle"

# Generate default HD wallpaper backgrounds via Python stdlib
python3 -c "
import struct, zlib
def make_png(filename, r, g, b, width=1920, height=1080):
    raw_data = bytes([0] + [r, g, b] * width) * height
    compressed = zlib.compress(raw_data)
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    with open(filename, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', compressed))
        f.write(chunk(b'IEND', b''))
make_png('$ROOTFS/usr/share/backgrounds/gallos/default.png', 30, 30, 46)
make_png('$ROOTFS/usr/share/backgrounds/gallos/contest.png', 46, 20, 20)
"

# Graphical Kiosk Autologin on tty1
mkdir -p "$ROOTFS/etc/systemd/system/getty@tty1.service.d"
cat > "$ROOTFS/etc/systemd/system/getty@tty1.service.d/autologin.conf" <<'EOF'
[Unit]
ConditionPathExists=/run/gallos/kiosk-ready

[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin contestant --noclear %I $TERM
EOF

# Profile session launcher on tty1: executes labwc -C /etc/xdg/labwc
cat > "$ROOTFS/etc/profile.d/gallos-kiosk.sh" <<'EOF'
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export XDG_CURRENT_DESKTOP=labwc
    export MOZ_ENABLE_WAYLAND=1
    export QT_QPA_PLATFORM=wayland
    export GDK_BACKEND=wayland
    export XDG_CONFIG_DIRS=/etc/xdg
    exec dbus-run-session labwc -C /etc/xdg/labwc
fi
EOF
chmod +x "$ROOTFS/etc/profile.d/gallos-kiosk.sh"

# Serial console ttyS0 autologin for automated testing
mkdir -p "$ROOTFS/etc/systemd/system/serial-getty@ttyS0.service.d"
cat > "$ROOTFS/etc/systemd/system/serial-getty@ttyS0.service.d/autologin.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin contestant --noclear %I $TERM
EOF

# Install casper live-boot hook
echo "Installing casper hook: 55gallos-live"
install -m 0755 \
    "$REPO_ROOT/vendor/inherited/maratona-casper/55gallos-live" \
    "$ROOTFS/usr/share/initramfs-tools/scripts/casper-bottom/55gallos-live"

# Patch casper's own scripts/casper to mount .gsm SquashFS software modules
# into the OverlayFS union (ROADMAP.md Phase 1 "Casper Live Boot Engine";
# see vendor/inherited/maratona-casper/casper-gsm-overlay.sh for why this
# must be a build-time patch to setup_overlay() rather than a casper-bottom
# hook). Fails the build loudly if the anchors it depends on have drifted.
echo "Patching casper for .gsm module mounting..."
sh "$REPO_ROOT/vendor/inherited/maratona-casper/casper-gsm-overlay.sh" \
    "$ROOTFS/usr/share/initramfs-tools/scripts/casper"

# Install gallos-daemon and gallos-ctl. Installed under the module name
# gallos_daemon (underscore, not gallos-daemon's hyphen) because main.py's
# sibling modules use package-relative imports (`from .config import ...`)
# — those only resolve when main.py is run as `python3 -m gallos_daemon.main`
# (see gallos-daemon.service's ExecStart/WorkingDirectory), and `-m` needs a
# syntactically valid Python package/module name.
echo "Installing gallos-daemon and gallos-ctl..."
mkdir -p "$ROOTFS/usr/libexec/gallos_daemon"
cp -r "$REPO_ROOT/daemon/src/"* "$ROOTFS/usr/libexec/gallos_daemon/"
chmod -R 0755 "$ROOTFS/usr/libexec/gallos_daemon"
install -m 0755 "$REPO_ROOT/daemon/gallos-ctl" "$ROOTFS/usr/bin/gallos-ctl"
ln -sfn gallos-ctl "$ROOTFS/usr/bin/gallosctl"

chroot "$ROOTFS" update-initramfs -c -k all

echo "Stage 2 complete."
