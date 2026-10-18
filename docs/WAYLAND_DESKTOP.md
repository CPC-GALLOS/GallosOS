# GallosOS Wayland Kiosk Desktop Specification

This document defines the architectural rationale, component selection, dotfile structure, security requirements, and intended user experience for the **GallosOS Wayland Kiosk Session**.

For the broader system architecture, see [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md). For configuration schema and runtime directives, see [`docs/CONFIG_SPEC.md`](./CONFIG_SPEC.md).

## Implementation status

The specification includes future Phase 4 behavior. Checkboxes in [`ROADMAP.md`](../ROADMAP.md) track implementation, with image/graphical acceptance recorded separately.

| Area | Current source behavior | Remaining work |
| :--- | :--- | :--- |
| Base session | Labwc, Waybar, Foot, Mako, and launcher configuration are generated. | Accept the actual contestant session on a built image. |
| App menu | The configured action invokes `wmenu-run`. | Implement the specified mode-aware application allowlist. |
| Mode and countdown | Waybar displays static `MODE: DEFAULT` and standby text; the daemon separately exports state. | Connect the displayed controls to runtime state. |
| Clock | The generated format is `HH:MM`. | Implement the precision/relaxed/hidden cycle below. |
| Keyboard | Shortcuts invoke a helper that cycles `us`, `latam`, `es`, `br` in `/tmp/gallos_layout` and sends a notification. | Apply actual compositor/XKB changes, consume configured layouts, and add a Waybar indicator/control. |
| Low memory and audio | EarlyOOM broadcasts are configured; mode-aware audio is specified. | Implement the desktop notification bridge and effective audio policy. |

The target controls below are not claims of completed implementation or graphical acceptance.

---

## 1. Design Philosophy & Architectural Rationale

Traditional competitive programming live distributions (including HuronOS and legacy ICPC environments) have historically relied on X11 desktop environments (such as Solus Budgie, XFCE, or Openbox). While familiar, X11 presents critical architectural vulnerabilities:

1. **X11's Shared Client Access:** Traditional X11 sessions allow broader inter-client access to input and window contents than Wayland's compositor-mediated client model. Wayland narrows that access but does not create a complete anti-cheat boundary or replace process isolation and policy enforcement.
2. **Bloat of Full Desktop Environments:** Mainstream desktop environments (GNOME, KDE Plasma, Budgie) pull extensive dependency trees and background daemons (indexing services, system settings daemons, tracker miners), increasing ISO size, RAM consumption, and flashing times.
3. **Exploitable Setting Panels:** Desktops with rich GUI control centers expose network management and display settings that contestants can tamper with during a competition.

### Why the Wayland Kiosk Stack?

GallosOS replaces X11 with a customized, lightweight **Wayland Kiosk Session**:

```mermaid
graph TD
    subgraph "Wayland Compositor (Root & Session Control)"
        Labwc[Labwc Stacking Compositor]
        WLRoots[wlroots / Wayland Core]
    end

    subgraph "Desktop Shell & UI (Low Memory Footprint)"
        Waybar[Waybar Status Bar]
        Menu[Application Launcher]
        Mako[Mako Notification Server]
        Swaybg[swaybg Wallpaper Daemon]
    end

    subgraph "Client Applications (Unprivileged Session Processes)"
        Foot[Foot Wayland Terminal]
        IDEs[IDEs: VSCodium, JetBrains, Geany]
        Browser[Selected Browser: Firefox]
        Docs[Offline Docs Viewer (Planned)]
    end

    Labwc --> WLRoots
    Labwc --> Waybar
    Labwc --> Mako
    Labwc --> Swaybg
    Waybar --> Menu
    Labwc --> Foot
    Labwc --> IDEs
    Labwc --> Browser
    Labwc --> Docs
```

---

## 2. Core Desktop Components

| Component | Software | Role & Rationale |
| :--- | :--- | :--- |
| **Compositor** | **Labwc** | Stacking Wayland compositor inspired by Openbox. Wayland client access is compositor-mediated; this is not kernel process isolation. |
| **Status Bar** | **Waybar** | CSS-styled bar. Current configuration shows static mode/countdown text and a minute-resolution clock; dynamic controls remain planned. |
| **Terminal** | **Foot** | Wayland-native terminal emulator. Resource use has not been empirically benchmarked for GallosOS. |
| **Notifications** | **Mako** | Wayland notification daemon. EarlyOOM and administrative-message integrations remain planned. |
| **Wallpaper** | **swaybg** | Minimal Wayland wallpaper utility rendering contest-specific or university-branded backgrounds. |
| **Seat Management** | **seatd** | Minimal, rootless seat management daemon providing unprivileged DRM/KMS and input device access. |
| **Display Control** | **wlr-randr** | Minimal command-line tool for Wayland display resolution and scaling management. |
| **App Launcher** | **wmenu** | Wayland launcher invoked from Waybar. Organizer-policy allowlisting is not implemented in the current launcher. |

### 2.1 GPU Backend Note (Proprietary Driver Compatibility)

Labwc's `wlroots` backend renders via GBM/EGL. On machines running the opt-in `drivers/nvidia-proprietary` module (`docs/HARDWARE_COMPATIBILITY.md` § 1.3), correct Wayland compositing depends on the installed NVIDIA driver version shipping working GBM support — older proprietary driver releases historically required the separate `wlroots` EGLStreams codepath instead. No specific minimum driver version is certified here; this is a compatibility dimension organizers enabling the proprietary module should verify against the driver version their `build.toml` pins. The default Nouveau/`amdgpu`/`i915` path is unaffected.

---

## 3. Immutable Configuration & Tamper Resistance

To maintain tournament integrity, desktop configuration files (dotfiles) are **pre-configured, root-owned, and protected against contestant tampering**:

1. **System-Level Overrides (`/etc/xdg/`):**
   Authoritative desktop dotfiles reside in system-level paths (`/etc/xdg/labwc/`, `/etc/xdg/waybar/`, `/etc/xdg/foot/`, `/etc/xdg/mako/`).
2. **Explicit Kiosk Configuration Loading (`labwc -C /etc/xdg/labwc`):**
   Upstream `labwc` defaults to checking `${XDG_CONFIG_HOME:-$HOME/.config}/labwc` before `/etc/xdg/labwc` without merging. To prevent a contestant from bypassing restrictions by writing a local `~/.config/labwc/rc.xml`, the kiosk session launcher explicitly executes `labwc -C /etc/xdg/labwc` without `--merge-config`.
3. **Read-Only SquashFS Layer:**
   These configurations are baked into the immutable SquashFS base layer. Even if a contestant modifies local files during a session, the baseline settings cannot be permanently corrupted, and a reboot restores the pristine environment.
4. **No Unprivileged Desktop Settings GUI:**
   GallosOS intentionally excludes settings panels (like `gnome-control-center` or `xfce4-settings`). System configuration (display resolution, timezone, keyboards) is handled declaratively beforehand via `gallos.toml`.

---

## 4. Keybindings & Desktop Controls

All keybindings are centralized within `/etc/xdg/labwc/rc.xml` and enforced authoritatively by Labwc via `labwc -C /etc/xdg/labwc`.

> [!NOTE]
> **The `Super` Key:** In Linux documentation, the **`Super`** key refers to the **Windows key ($\mathbf{\boxplus}$)** on standard PC keyboards, or the **Command key ($\mathbf{\⌘}$)** on Apple Mac keyboards.

### 4.1 Global Hotkeys

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **`Super + Space`** | Keyboard helper | Invokes the partial helper; actual layout switching remains planned. |
| **`Alt + Shift`** | Keyboard helper | Invokes the same partial helper as a fallback shortcut. |
| **`Super + Return`** | Launch Foot Terminal | Opens a new Foot terminal instance. |
| **`Alt + Tab`** | Window Switcher | Switches focus between open contestant application windows. |
| **`Super + Q` / `Alt + F4`** | Close Window | Closes the active client window. |

Both keyboard layout shortcuts invoke the session helper at `/usr/bin/gallos-layout-toggle`.

The helper currently writes a layout name and reports it through `notify-send`; it does not apply that layout. Do not use the notification as evidence of active keyboard state.

### 4.2 Security Restrictions

- **Virtual Terminal (VT) Console Switch Lockout:** Keybindings for switching virtual terminals (`Ctrl+Alt+F1` through `Ctrl+Alt+F6`) are explicitly disabled at the compositor level. In legacy X11 distributions like huronOS, contestants pressing IDE shortcuts (e.g. VS Code comment toggles or Fn shortcuts) routinely triggered accidental VT switches to raw text prompts, leading to panic reboots, DHCP IP churn, and subsequent BOCA judge "IP Warning" lockouts.
- **Restricted Spawning:** Dangerous shortcuts that could break desktop kiosk integrity (such as spawning arbitrary unvetted desktop shells or executing raw system commands outside the whitelisted menu) are completely excluded from `/etc/xdg/labwc/rc.xml`.

---

## 5. Waybar Ergonomics & Custom Modules

The following target design for `Waybar` is Phase 4 work. The current generated configuration is summarized above; the diagram is a proposed layout.

```text
+---------------------------------------------------------------------------------------------------+
| [ Gallos Menu ]  [Active Task]                   [ Countdown: 02:45:10 ]  [LATAM]  [14:32:08] [RAM] |
+---------------------------------------------------------------------------------------------------+
```

1. **Whitelisted Application Menu (Planned):**
   - A clean dropdown launcher anchored to the left of the bar.
   - Exposes strictly authorized contest applications (IDEs, Terminal, Docs, Browser) according to the active mode (`Contest`, `Event`, or `Default`).
2. **Dynamic Contest Countdown (Planned):**
   - Local script polling `gallosd` state. Displays remaining time (e.g. `Time Left: 02:45:10`) and flashes amber when under 15 minutes remain.
3. **Interactive Stress-Free Clock (Planned):**
   - Clicking directly on the clock widget cycles between:
     $$\text{Full Precision (HH:MM:SS)} \longrightarrow \text{Relaxed (HH:MM)} \longrightarrow \text{Focus Mode (Hidden)}$$
4. **Keyboard Layout Indicator & Switcher:**
   - **Planned:** A badge showing the actual compositor layout, with a click action that applies the next Organizer-configured layout. No keyboard module is currently included in the generated bar.
5. **EarlyOOM Low-Memory Indicator (Planned):**
   - Add a visible status indicator; the current Waybar has no such module.
6. **Mode-Aware Power Controls (Planned):**
   - Apply specified shutdown/reboot controls by mode; these controls are not integrated with daemon state.

---

## 6. Unified Visual Styling & Typography

The target desktop style is a neutral dark theme across the selected Wayland and XWayland applications. Installed-package availability and graphical rendering still require image acceptance:

- **Status Bar Icon Font:** Ubuntu 24.04's `fonts-font-awesome` package provides the `FontAwesome` family (Font Awesome 4.7). Waybar uses glyphs from that version for `` Wi-Fi, `` Ethernet, `` Offline, and `` Clock. The build refreshes the font cache after provisioning; rendering still needs graphical-session verification.
- **UI & Contest Platform Font:** `Inter` (matches modern contest platforms like MOJ that specify `font-family: "Inter"` without bundling webfonts), with `Liberation Sans` and `DejaVu Sans` as universal offline fallbacks.
- **Monospace Font:** `Liberation Mono` and `DejaVu Sans Mono` (configured in Foot terminal and Mako notifications) alongside `JetBrains Mono` for contestant code editors.
- **Full Color Emoji & Unicode Fallback:** `Noto Color Emoji` is installed and added through fontconfig (`/etc/fonts/conf.d/56-fonts-noto-color-emoji.conf`) as a fallback for `sans-serif`, `serif`, and `monospace`. Emoji rendering in browsers and desktop widgets still needs graphical-session verification.
- **Theme Palette:** Neutral dark background (`#1e1e2e` Catppuccin Mocha) with high-contrast text (`#cdd6f4`) and subtle accents, reducing eye strain during 5-hour contest sessions.
- **GTK/Qt Consistency:** Unified GTK3/GTK4 dark theme (`Adwaita-dark` / `Arc-Dark`) applied globally to Geany, VSCodium, JetBrains, and Chromium without requiring full desktop background daemons.

---

## 7. Audio Subsystem (PipeWire & WirePlumber)

The schema describes a PipeWire-based audio policy. The current build/runtime does not install or apply an effective per-mode audio policy.

### 7.1 Contest vs. Practice Audio Policy

The intended audio policy below is not yet wired to effective session controls. Phase 4 must implement and verify it before `allow_audio` can be described as enforcing mute/disable behavior.

- **Contest Mode (Disabled / Muted by Default):**
  - Live competitive programming contests (such as ICPC and IOI) are held in strict low-noise environments.
  - To prevent accidental noise, notification dings, or rogue audio cues, the PipeWire master output is **muted and disabled by default** during active `Contest` windows (`allow_audio = false`).
- **Event & Default Modes (Enabled for Training & Lectures):**
  - Audio output is fully enabled (`allow_audio = true`) during training camp lectures, classroom practice, and upsolving sessions, allowing contestants to watch tutorial videos, algorithm lectures (e.g. YouTube / course portals), and participate in remote debriefs.
