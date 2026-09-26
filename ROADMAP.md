# GallosOS Development Roadmap & Feature Tracker

This document translates the complete architectural and security specifications across all design documents (`ARCHITECTURE.md`, `CONFIG_SPEC.md`, `ANTI_CHEAT_AND_SECURITY.md`, `HARDWARE_COMPATIBILITY.md`, `COMPARATIVE_ANALYSIS.md`, and `PROVENANCE.md`) into a concrete, actionable engineering roadmap.

> **MVP Scope Definition:** The Minimum Viable Product (MVP) consists strictly of **Phase 1 through Phase 3**. Completing Phase 3 yields a fully functional, highly secure, drop-in replacement for HuronOS ready for local deployments. Phase 4 onwards represent polish, tooling, and post-GA telemetry.

---

## Phase 1: Bootstrapping, Casper & Core Filesystem Engine (Alpha)

*Goal: Build a containerized build pipeline producing a bootable Ubuntu 24.04 LTS Live ISO/USB supporting both UEFI SecureBoot and Legacy BIOS with Wayland.*

- [x] **OCI Build Container:** Create the `Containerfile` / `Dockerfile` (Podman/Docker) to bootstrap an `ubuntu:24.04` minimal rootfs without host pollution.
- [x] **Dual Bootloader Chain:** Configure hybrid bootloaders supporting:
  - UEFI Boot via GRUB (unsigned binary in initial walking skeleton; signed Canonical shim/GRUB chain in subsequent increment).
  - Legacy PC-BIOS (CSM) via `grub-pc` and MBR boot sector.
- [x] **Casper Live Boot Engine:** Configure `casper` boot parameters and hooks:
  - [x] Basic home seeding and overlay assembly hook (`vendor/inherited/maratona-casper/55gallos-live`).
  - [x] Mount SquashFS modules (`.gsm`) into union layers using in-tree **OverlayFS** (build-time patch to casper's own `setup_overlay()`, `vendor/inherited/maratona-casper/casper-gsm-overlay.sh` — casper-bottom hooks run after the overlay is already assembled, so this can't be a hook). QEMU-verified: `mount` shows `lowerdir=/test.gsm:/filesystem.squashfs`, correctly composes with `toram`.
  - [x] Automatically mount the 2-partition Live USB layout (`GALLOS_BOOT`, optional `event-data`) by filesystem label. GALLOS_BOOT exposure via `55gallos-live`'s `/boot/gallos` symlink (QEMU-verified: real `gallos.toml` content readable post-boot). `event-data` label-mount is owned by `gallos-daemon` (`daemon/src/storage.py`), not casper, since mounting it is mode-aware (never during Contest) and that precedence already lives in `ModeStateMachine` — QEMU-verified the mount itself succeeds, but see the note below: it's currently only visible inside the daemon's own sandboxed mount namespace, not to the desktop session, which is a separate follow-up.
  - [x] Support the `toram` boot parameter (copy entire OS to RAM) — stock upstream Ubuntu `casper` behavior, not GallosOS-authored; QEMU-verified (`copy_live_to()`'s tmpfs RAM copy triggers correctly with `toram` on the cmdline).
  - [x] Support `gallos.config=<path_or_url>` and Ventoy `/gallos/gallos.toml` detection. Cmdline parsing was already implemented in `daemon/src/config.py`; `55gallos-live` adds the Ventoy-partition scan (content-based, not label-fingerprinted) and copies the found file into place. QEMU-verified: a synthetic Ventoy-like fixture's `gallos.toml` is readable post-boot.
- [x] **SquashFS Packaging Scripts:** Write `build-squashfs.sh` to package system layers with `mksquashfs -comp zstd`.
- [x] **Hybrid ISO Stitched Image:** Write `build-iso.sh` using `xorriso` / `grub-mkrescue` to generate hybrid bootable `.iso` images.
- [x] **Wayland Kiosk Desktop Shell:** Assemble the lightweight desktop environment:
  - `labwc` Wayland compositor configured with per-client security isolation.
  - `Waybar` status bar configured with an integrated dropdown application launcher, countdowns, network status, and layout switchers.

---

## Phase 2: Security Lockdown, Anti-Cheat Shield & Resource Hardening (Beta 1)

*Goal: Enforce strict Zero-Trust contest integrity, network air-gapping, and out-of-memory protections.*

- [x] **Anti-Cheat Enforcement (`nftables`):**
  - [x] Implement default DROP policy (Zero-Trust), IPv4-only (`table ip`)
  - [x] Disable IPv6 network-wide (kernel `ipv6.disable=1` + `/etc/sysctl.d/99-gallos-noipv6.conf`) — huronOS precedent, avoids a dual-stack firewall bypass
  - [x] Static IP / CIDR whitelisting for Judge Servers (`[security]` build-time posture; dynamic `gallos.toml` runtime rendering in Phase 3)
  - [x] Port-locking (block outbound 22, 853, and telemetry DNS list; STUN / hole-punching heuristics deferred to daemon phase)
- [x] **Peripheral & USB Lockdown:**
  - Deny USB mass-storage via modern `polkit`/`udisks2` JavaScript rules (`99-gallos-usb-block.rules` for the `contestant` user) with dynamic `udev` unbind rules (`99-contest-usb-block.rules`) as a fallback. Allow mice, keyboards, and HID in both cases.
- [x] **TTY & Privilege Hardening:**
  - Disable virtual terminal switching (TTY1–6) via `logind.conf.d/99-gallos-novt.conf`, masked `autovt@.service`, and kernel keymap remapping (`gallos-novt-keymap.service`).
  - Configure the `contestant` user as unprivileged without `sudo` (purged) or administrative rights, and locked `root` account.
- [x] **EarlyOOM Guard (`earlyoom -n` + `systembus-notify`):**
  - Configure `earlyoom -n` (D-Bus broadcast) and enable `earlyoom.service` (`systembus-notify` desktop bridge and `oom_score_adj` protection of `gallos-daemon`/browsers deferred to Phase 3 when those processes exist).

---

## Phase 3: Daemon, Mode State Machine & Dynamic Directives (Beta 2)

*Goal: Implement the real-time configuration engine, multi-mode scheduling, and network sync.*

- [x] **`gallos-daemon` Core Engine:**
  - Develop a persistent `systemd.service` (Python) capable of maintaining state and open sockets for real-time broadcasts.
  - Implement strict TOML parsing and schema validation against `schema/directives.schema.json` via `taplo`.
  - `gallosd` systemd unit alias (`Alias=gallosd.service` in `daemon/gallos-daemon.service`), so `systemctl status/restart gallosd` also works for sysadmins who assume a generic `<name>d` daemon name.
- [x] **Hybrid Config Ingestion & Fallback:**
  - Implement boot sequence logic: attempt to fetch a remote `gallos.config=<url>` with a 5-second timeout; if unreachable, gracefully fall back to local `/boot/gallos/gallos.toml` cache with Plymouth/desktop warnings.
  - Support multi-profile selection via kernel boot arguments.
- [x] **3-Tier Precedence State Machine:**
  - Implement dynamic scheduling engine: $\text{Contest} \succ \text{Event} \succ \text{Default}$.
  - Transition wallpapers, network firewall rules, and application visibility automatically when contest time-windows start or expire.
- [x] **Dynamic Hot-Reload Hooks:**
  - Instantaneous wallpaper switching on mode transitions.
  - Dynamic `nftables` rule updates on the fly without rebooting.
- [x] **Post-Contest Workspace Support:**
  - Re-enable USB mass-storage drivers and provide visual prompts for manual code extraction.
- [x] **Machine Identity & Team Assignment:**
  - Assign workstation hostnames via DHCP MAC reservations or per-USB `machine.toml` directives.

> **Known issues found during Phase 1's QEMU boot verification** (this was the first time `gallos-daemon` was actually booted end-to-end via `test-iso-qemu.sh` rather than only unit-tested — `daemon/tests/` mocks every `subprocess`/filesystem call, so none of these were previously exercised):
> - **Fixed in this pass:** `gallos-daemon.service` crash-looped on every boot (`ProtectSystem=strict` + `ReadWritePaths=` requires listed paths to pre-exist; `/etc/chromium/policies/managed`, `/etc/firefox/policies`, and `/media/event-data` didn't — fixed by pre-creating them in `build/scripts/03-harden.sh`); `main.py` failed with `ImportError: attempted relative import with no known parent package` when invoked as a plain script (fixed by installing under a valid module name `gallos_daemon` and invoking via `python3 -m gallos_daemon.main`, see `daemon/gallos-daemon.service` and `build/scripts/02-provision.sh`); `ModeStateMachine` never called `mount_event_data()`/`_switch_open_mode()` on a boot straight into Default mode, since `current_mode` started pre-equal to the first evaluated target (fixed with a `_BOOT_SENTINEL_MODE` in `daemon/src/state_machine.py`); `_is_schedule_active()` assumed `contest.schedule`/`event.schedule` were single `{start_time, end_time}` dicts, but `schema/directives.schema.json`'s `time_window` (and every `examples/*.toml`) defines `schedule` as an array of `{start, end}` objects — every real profile's `[[contest.schedule]]` crashed the main loop on every iteration (fixed in `daemon/src/state_machine.py`; the pre-existing test in `daemon/tests/test_state_machine.py` was asserting against the wrong shape too, also fixed).
> - **MVP stabilization in progress:** event-data mount operations use a separate host-namespace systemd service; transition errors keep the contestant kiosk stopped and expose a local root recovery prompt when configured; the ISO builder uses Ubuntu's signed EFI boot chain. A complete Live-image QEMU run verified local root login, a busy-mount transition failure with the recovery console active, manual retry into Contest, return to Default, and preserved event data. Physical hardware and graphical contestant-session behavior remain acceptance gates before Phase 4.

---

## Phase 4: Specialized Contest Subsystems & Branding (Beta 3)

*Goal: Deliver printing, proctoring, white-labeling, and offline reference capabilities.*

- [ ] **`gallos-print` CUPS Subsystem:**
  - Develop the `gallos-print` CLI for contestants (`gallos-print solution.cpp`), inspecting and adapting the proven `printfile` (`a2ps` / `enscript`) pipeline pattern from `icpcsysops/ansible` and SWERC Lyon.
  - Support standard browser/judge GUI printing (`Ctrl + P` in Chromium / Firefox) through the default virtual CUPS queue.
  - Implement screenshot/window capture printouts via `grim` (`gallos-print --screenshot`).
  - Build `gallos-cups-filter` to inject syntax highlighting, line numbering, team metadata headers, timestamps, and page numbers.
  - Enforce printer whitelisting in `gallos.toml` to prevent unauthorized network print jobs.
- [ ] **Rapid White-Labeling & Branding Engine:**
  - Offline Plymouth boot splash generator from `boot_splash_logo_url`.
  - Custom CSS/GTK theme and wallpaper injector for Labwc and Waybar with optional `show_powered_by_gallos` watermark.
  - Custom GRUB boot menu background + colors (MVP: single-entry background/menu-color theming; a full `theme.txt` with per-entry icons is a later extension once multiple boot entries exist).
  - Ubuntu-branding removal pass (Plymouth splash, `/etc/os-release`/`lsb-release` `PRETTY_NAME`, pending trademark-policy verification) so the live OS reads as GallosOS rather than a visibly-reskinned Ubuntu.
  - Full design: [`docs/BOOT_BRANDING.md`](./docs/BOOT_BRANDING.md).
- [ ] **Keyboard Layout Switcher:**
  - Provision and expose Waybar switcher module for configured layouts (`latam`, `us`, `es`, etc.).
- [ ] **Offline Documentation & Translation:**
  - Bundle static HTML documentation packages (`cppreference-doc-en-html`, `python3-doc`, `openjdk-21-doc`).
  - Pre-configure browser bookmarks pointing to `file:///usr/share/doc/`.
  - Bundle lightweight offline dictionary (`GoldenDict` or `stardict`) with EN-ES / EN-PT databases to solve the translation firewall gap without bloating RAM.
- [ ] **`base_os` Version Flexibility (`build.toml`):**
  - Formalize the maintainer-tested-default vs. community-supported `base_os` tiers in the build pipeline (`ubuntu-22.04-minimal`, `ubuntu-26.04-minimal`, interim non-LTS releases) per `docs/ARCHITECTURE.md` §3.1.
  - Document the `kernel` (HWE) pairing needed when targeting newer hardware than an older `base_os` release ships by default.
- [ ] **Proprietary GPU Driver Support (`drivers/nvidia-proprietary`):**
  - Package the opt-in NVIDIA proprietary driver as a DKMS-carrying `.gsm` module per `docs/ARCHITECTURE.md` §4.
  - Implement the MOK signing-key generation/persistence step in `gallos-builder` (`docs/BUILD_SYSTEM.md` §4) and document the one-time per-machine `mokutil --import` venue-setup flow (`docs/HARDWARE_COMPATIBILITY.md` §1.3).
  - **Future dependency:** a `langs/programming/cuda-toolkit` module (nvcc, cuDNN) for CUDA programming sessions depends on this driver work landing first — not scoped or specified yet.

---

## Phase 5: Organizer Tooling Suite (RC 1)

*Goal: Build standalone utilities for mass USB preparation, migration, and visual configuration.*

- [ ] **`gallos-convert` (HuronOS Migration CLI):**
  - Parser for legacy `.hdf` configuration formats into canonical `gallos.toml`.
  - Include `--validate` (taplo schema check) and `--diff` CLI flags.
- [ ] **`gallos-flash` (Mass Multi-USB Flashing Tool):**
  - Multi-threaded parallel writer supporting 50+ simultaneous USB targets.
  - Native support for Linux, macOS, and Windows WSL2 via `usbipd-win`.
  - Automatic creation of a FAT32 `GALLOS_BOOT` partition plus an ext4 `event-data` partition sized to consume all remaining drive capacity. No `contest-data` partition — `Contest` mode never persists to the boot drive (see `docs/ARCHITECTURE.md` §4, item 5).
  - Native unattended/scriptable CLI operation as a first-class interface (structured flags, no interactive-prompt patching required) — a real-world lab-deployment requirement identified from huronOS's own installer lacking one (`docs/COMPARATIVE_ANALYSIS.md` §4, item 16).
  - Concurrent-safe multi-instance operation with no shared global mount points or system-wide mutable state, so multiple simultaneous flashing runs (including a Windows/WSL2 run alongside a native Linux run) cannot race each other (`docs/COMPARATIVE_ANALYSIS.md` §4, items 17–18).
- [ ] **`gallos-inject` (In-Place USB Delta Updater CLI):**
  - In-place delta updater for already-provisioned GallosOS USB drives, avoiding full-disk re-flashing and preserving partition tables and MBR/GPT sectors.
  - **Tier 1 (Configuration & Branding):** Direct filesystem replacement of `gallos.toml` and `wallpaper.png` on the FAT32 `GALLOS_BOOT` partition without SquashFS repacking.
  - **Tier 2 (Modular `.gsm` Packages):** Dynamic addition, removal, or update of standalone software modules (`/gallos/modules/*.gsm`) stacked automatically into OverlayFS at boot.
  - **Tier 3 (Custom Layer Overrides):** Unsquashes, patches, and rebuilds the top `99-custom.gsm` system layer (e.g. for custom drivers, udev rules, or emergency scripts) with automatic checksum recalculation.
  - **Tier 4 (Bootloader Tuning):** In-place tuning of GRUB kernel parameters (`toram`, display driver flags) in `/boot/grub/grub.cfg` and `/EFI/BOOT/grub.cfg`.
  - **Multi-Device Batch Mode:** Concurrently detect and update all mounted USB drives labeled `GALLOS_BOOT`.
- [ ] **GallosOS Config Builder (Web & GUI App):**
  - Interactive web application (Angular) hosted on GitHub Pages or locally.
  - Visual time-picker for contest schedule, checkbox module selector, firewall IP list builder, and live TOML preview/download.

---

## Phase 6: Software Toolchains, Virtual Appliances & CI/CD (GA Release)

*Goal: Package contest programming languages, IDEs, VM targets, and automated build pipelines.*

- [ ] **Compilers & Runtimes:**
  - Package and verify standard contest toolchains (cross-referencing package manifests from `icpc-environment/icpc-env`, `maratona-linux/maratona-team-tools`, and `ioi-2025/contestant-vm`): GCC (C/C++), Clang, OpenJDK 21 (Java), Python 3, PyPy3, Rust, Kotlin, Mono / .NET.
- [ ] **Contestant IDEs:**
  - Pre-configure and package VSCodium (with offline extensions), JetBrains Community Edition (IntelliJ IDEA, PyCharm), CLion (with activation script), Code::Blocks, Geany, Kdevelop, Neovim (lazyvim), Vim (linters, plugins), and Kate.
  - Offline extension-registry robustness for VSCodium `.gsm` modules: no marketplace dependency, correct extension-ID normalization, and correct write permissions preserved across every module's OverlayFS layer — lessons from huronOS's own offline-`.vsix` fragility (`docs/COMPARATIVE_ANALYSIS.md` §4, item 9).
- [ ] **Anti-Cheat Purge & Telemetry Neutralization (Post-MVP):**
  - Write a startup service to purge `com.intellij.ml.llm` and Copilot plugins from JetBrains and VSCodium installations.
  - Neutralize telemetry and crash reporting in Chromium, Firefox, and VSCodium.
- [ ] **Virtual Machine Appliances:**
  - Automated building of `.ova` (VirtualBox / VMware) and `.qcow2` (KVM/QEMU) appliances.
  - Pre-configure guest additions and display resizing for virtualization.
- [ ] **Public Documentation Site:**
  - Deploy an official Docusaurus or GitBook site for user-facing documentation, quickstarts, and architectural deep-dives.
- [ ] **CI/CD & Release Automation:**
  - GitHub Actions workflow to build release ISOs inside OCI containers on Git tags.
  - Automated smoke tests in headless QEMU to verify boot, firewall default-DROP, and daemon operation.

---

## Phase 7: Venue Controller & Advanced Telemetry (Post-GA / v2.0)

*Goal: Centralized infrastructure for massive deployments, fleet monitoring, and automated auditing.*

- [ ] **Venue Controller Server Mode:**
  - Dedicated GallosOS boot mode to act as the central orchestrator (DHCP, NTP, MAC mapping).
- [ ] **Administrative Proctoring, Auditing & Keystroke Forensics:**
  - Adopt/fork the **`martkeys`** daemon architecture (`icpcsysops/ansible`) for kernel-level `/dev/input/event*` keystroke and mouse activity aggregation (Wayland compositor-agnostic) when `enable_keystroke_forensics = true`.
  - Implement scheduled background screenshot captures via dedicated root Wayland socket.
  - Bundle `node-exporter` and `gallos-exporter` for real-time fleet health metrics.
  - Build `gallos-audit-export` CLI to aggregate and export ephemeral workstation logs, EarlyOOM kill events, firewall drops, `martkeys` activity metrics, print history, and proctoring snapshots into a persistent `gallos-audit-YYYYMMDD.tar.gz` archive.
