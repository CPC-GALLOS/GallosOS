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
        python3-jsonschema \
        network-manager \
        locales \
        plymouth \
        plymouth-theme-ubuntu-text \
        zstd \
        fontconfig \
        fonts-font-awesome \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-color-emoji \
        fonts-inter \
        ${extra_pkgs[*]@Q}

    echo 'GallosOS' > /etc/hostname
    { echo overlay; echo squashfs; echo isofs; echo vfat; echo exfat; } >> /etc/initramfs-tools/modules

    # Create contestant user with video/input/render permissions
    useradd -m -s /bin/bash contestant || true
    usermod -a -G video,input,render contestant || true
    if getent group _seatd >/dev/null 2>&1; then
        usermod -a -G _seatd contestant || true
    fi
    if getent group vboxsf >/dev/null 2>&1; then
        usermod -a -G vboxsf contestant || true
    fi
    systemctl enable qemu-guest-agent.service || true
"

# Ubuntu 24.04's browser packages are Snap launchers. Install Mozilla's
# signed DEB repository so the Live image contains a real offline browser.
install -d -m 0755 "$ROOTFS/etc/apt/keyrings" "$ROOTFS/etc/apt/sources.list.d" "$ROOTFS/etc/apt/preferences.d"
curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg \
    -o "$ROOTFS/etc/apt/keyrings/packages.mozilla.org.asc"
mozilla_fingerprint="$(gpg --show-keys --with-colons "$ROOTFS/etc/apt/keyrings/packages.mozilla.org.asc" | awk -F: '$1 == "fpr" {print $10; exit}')"
if [[ "$mozilla_fingerprint" != "35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3" ]]; then
    echo "02-provision.sh: Mozilla signing-key fingerprint mismatch" >&2
    exit 1
fi
cat > "$ROOTFS/etc/apt/sources.list.d/mozilla.list" <<'EOF'
deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main
EOF
cat > "$ROOTFS/etc/apt/preferences.d/mozilla" <<'EOF'
Package: firefox
Pin: release o=Ubuntu
Pin-Priority: -1

Package: firefox
Pin: origin packages.mozilla.org
Pin-Priority: 1000
EOF
chroot "$ROOTFS" apt-get update
chroot "$ROOTFS" apt-get install -y --no-install-recommends firefox

# Release asset and digest are pinned together; never execute an unchecked IDE.
codium_version="1.135.06055"
codium_asset="codium_${codium_version}_amd64.deb"
codium_digest="5f5c00a9da9d232e4c84e9eee68bbdeb4d8737462022626ce3bdb6948f3d8649"
curl -fsSL "https://github.com/VSCodium/vscodium/releases/download/${codium_version}/${codium_asset}" \
    -o "$ROOTFS/tmp/$codium_asset"
printf '%s  %s\n' "$codium_digest" "$ROOTFS/tmp/$codium_asset" | sha256sum -c -
chroot "$ROOTFS" apt-get install -y --no-install-recommends "/tmp/$codium_asset"
rm -f "$ROOTFS/tmp/$codium_asset"

# Record the package versions embedded in this ISO for the release matrix.
mkdir -p "$ROOTFS/usr/share/gallos"
# dpkg-query expands these template fields, not Bash.
# shellcheck disable=SC2016
chroot "$ROOTFS" dpkg-query -W -f='${Package}\t${Version}\n' \
    gcc g++ clang openjdk-21-jdk python3 pypy3 rustc kotlin geany firefox codium \
    > "$ROOTFS/usr/share/gallos/toolchains.tsv"

# Contestant defaults are copied from /etc/skel after a fresh Contest entry.
mkdir -p "$ROOTFS/etc/skel/.config/VSCodium/User"
cat > "$ROOTFS/etc/skel/.config/VSCodium/User/settings.json" <<'EOF'
{
  "telemetry.telemetryLevel": "off",
  "update.mode": "none",
  "extensions.autoUpdate": false,
  "extensions.autoCheckUpdates": false
}
EOF
install -d -m 0755 "$ROOTFS/home/contestant/.config/VSCodium/User"
cp "$ROOTFS/etc/skel/.config/VSCodium/User/settings.json" \
    "$ROOTFS/home/contestant/.config/VSCodium/User/settings.json"
chroot "$ROOTFS" chown -R contestant:contestant /home/contestant/.config

# 2. Fontconfig alias & fallback configuration for Emoji and Symbols
mkdir -p "$ROOTFS/etc/fonts/conf.avail" "$ROOTFS/etc/fonts/conf.d"
cat > "$ROOTFS/etc/fonts/conf.avail/56-fonts-noto-color-emoji.conf" <<'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <match target="pattern">
    <test qual="any" name="family"><string>emoji</string></test>
    <edit name="family" mode="assign" binding="same"><string>Noto Color Emoji</string></edit>
  </match>
  <match target="pattern">
    <test name="family"><string>sans-serif</string></test>
    <edit name="family" mode="append"><string>Noto Color Emoji</string></edit>
  </match>
  <match target="pattern">
    <test name="family"><string>serif</string></test>
    <edit name="family" mode="append"><string>Noto Color Emoji</string></edit>
  </match>
  <match target="pattern">
    <test name="family"><string>monospace</string></test>
    <edit name="family" mode="append"><string>Noto Color Emoji</string></edit>
  </match>
</fontconfig>
EOF
ln -sf ../conf.avail/56-fonts-noto-color-emoji.conf "$ROOTFS/etc/fonts/conf.d/56-fonts-noto-color-emoji.conf"

# 3. System-wide dotfiles for Wayland Kiosk (/etc/xdg/)
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
    <context name="Title">
      <mousebind button="Left" action="Drag"><action name="Move" /></mousebind>
      <mousebind button="Left" action="DoubleClick"><action name="ToggleMaximize" /></mousebind>
    </context>
    <context name="Frame">
      <mousebind button="Left" action="Drag"><action name="Resize" /></mousebind>
    </context>
    <context name="Client">
      <mousebind button="Left" action="Press"><action name="Focus" /><action name="Raise" /></mousebind>
      <mousebind button="Right" action="Press"><action name="Focus" /><action name="Raise" /></mousebind>
    </context>
  </mouse>
</labwc_config>
EOF

# Labwc Catppuccin Mocha theme configuration
cat > "$ROOTFS/etc/xdg/labwc/themerc" <<'EOF'
border.width: 1
window.active.border.color: #89b4fa
window.inactive.border.color: #313244

window.active.title.bg.color: #1e1e2e
window.active.label.text.color: #cdd6f4
window.inactive.title.bg.color: #181825
window.inactive.label.text.color: #6c7086

menu.border.width: 1
menu.border.color: #45475a
menu.items.bg.color: #1e1e2e
menu.items.text.color: #cdd6f4
menu.items.active.bg.color: #89b4fa
menu.items.active.text.color: #11111b
menu.items.padding.x: 8
menu.items.padding.y: 4
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
WLR_NO_HARDWARE_CURSORS=1
WLR_RENDERER_ALLOW_SOFTWARE=1
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
        "format": "{icon}",
        "icon-size": 18,
        "icon-theme": "Adwaita",
        "tooltip-format": "{title}",
        "on-click": "activate",
        "app_ids-mapping": {
            "foot": "foot"
        }
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
        "format-wifi": " {essid} ({signalStrength}%)",
        "format-ethernet": " {ipaddr}",
        "format-disconnected": " Offline",
        "tooltip-format": "{ifname}: {ipaddr}"
    },
    "clock": {
        "format": " {:%H:%M}",
        "tooltip-format": "{:%Y-%m-%d %A}"
    }
}
EOF

# Waybar styling
cat > "$ROOTFS/etc/xdg/waybar/style.css" <<'EOF'
* {
    border: none;
    border-radius: 0;
    /* Ubuntu's fonts-font-awesome provides FontAwesome 4; the other fonts cover text and emoji. */
    font-family: "FontAwesome", "Liberation Sans", "DejaVu Sans", "Noto Color Emoji", sans-serif;
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

#taskbar {
    padding: 0 4px;
}

#taskbar button {
    padding: 0 8px;
    margin: 3px 2px;
    color: #cdd6f4;
    background: transparent;
    border-radius: 4px;
    border-bottom: 2px solid transparent;
}

#taskbar button:hover {
    background: #313244;
}

#taskbar button.active {
    background: #45475a;
    border-bottom: 2px solid #89b4fa;
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

# Desktop file mapping for foot icon resolution
ln -sf org.codeberg.dnkl.foot.desktop "$ROOTFS/usr/share/applications/foot.desktop"

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

# Profile session launcher on tty1: executes labwc with automatic renderer fallback
cat > "$ROOTFS/etc/profile.d/gallos-kiosk.sh" <<'EOF'
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export XDG_CURRENT_DESKTOP=labwc
    export MOZ_ENABLE_WAYLAND=1
    export QT_QPA_PLATFORM=wayland
    export GDK_BACKEND=wayland
    export XDG_CONFIG_DIRS=/etc/xdg
    export WLR_NO_HARDWARE_CURSORS=1
    export WLR_RENDERER_ALLOW_SOFTWARE=1

    # Detect VirtualBox or hypervisors lacking hardware DRM EGL
    VIRT="$(systemd-detect-virt 2>/dev/null || true)"
    if [ "$VIRT" = "oracle" ] || grep -qiE "virtualbox|innotek" /sys/class/dmi/id/product_name /sys/class/dmi/id/sys_vendor 2>/dev/null; then
        export WLR_RENDERER=pixman
    fi

    START_TIME=$(date +%s)
    dbus-run-session labwc -C /etc/xdg/labwc
    EXIT_CODE=$?
    ELAPSED=$(( $(date +%s) - START_TIME ))

    # If labwc crashed immediately (< 3s) on EGL/hardware renderer, fail over to software pixman
    if [ "$EXIT_CODE" -ne 0 ] && [ "$ELAPSED" -lt 3 ] && [ "${WLR_RENDERER:-}" != "pixman" ]; then
        echo "[gallos-kiosk] Hardware renderer failed in ${ELAPSED}s. Falling back to pixman..."
        export WLR_RENDERER=pixman
        START_TIME=$(date +%s)
        dbus-run-session labwc -C /etc/xdg/labwc
        EXIT_CODE=$?
        ELAPSED=$(( $(date +%s) - START_TIME ))
    fi

    # If it still crashes immediately, pause briefly to prevent an agetty spinloop
    if [ "$EXIT_CODE" -ne 0 ] && [ "$ELAPSED" -lt 3 ]; then
        echo "[gallos-kiosk] Labwc session failed to start (exit code $EXIT_CODE). Retrying in 5 seconds..."
        sleep 5
    fi
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

# Install the gallosd Python module and gallosctl controller command.
echo "Installing gallosd and gallosctl..."
mkdir -p "$ROOTFS/usr/libexec/gallosd"
cp -r "$REPO_ROOT/daemon/src/"* "$ROOTFS/usr/libexec/gallosd/"
install -m 0644 "$REPO_ROOT/schema/directives.schema.json" \
    "$ROOTFS/usr/libexec/gallosd/directives.schema.json"
chmod -R 0755 "$ROOTFS/usr/libexec/gallosd"
install -m 0755 "$REPO_ROOT/daemon/gallosctl" "$ROOTFS/usr/bin/gallosctl"

# Rebuild system font cache
echo "Rebuilding font cache..."
chroot "$ROOTFS" fc-cache -f

chroot "$ROOTFS" update-initramfs -c -k all

echo "Stage 2 complete."
