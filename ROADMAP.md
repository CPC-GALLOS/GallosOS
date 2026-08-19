# GallosOS Development Roadmap & Feature Tracker

This document translates the complete architectural and security specifications across all design documents (`ARCHITECTURE.md`, `CONFIG_SPEC.md`, `ANTI_CHEAT_AND_SECURITY.md`, `HARDWARE_COMPATIBILITY.md`, `COMPARATIVE_ANALYSIS.md`, and `PROVENANCE.md`) into a concrete, actionable engineering roadmap.

> **MVP Scope Definition:** The Minimum Viable Product (MVP) consists strictly of **Phase 1 through Phase 3**. Completing Phase 3 yields a fully functional, highly secure, drop-in replacement for HuronOS ready for local deployments. Phase 4 onwards represent polish, tooling, and post-GA telemetry.

---

## Phase 1: Bootstrapping, Casper & Core Filesystem Engine (Alpha)

*Goal: Build a containerized build pipeline producing a bootable Ubuntu 24.04 LTS Live ISO/USB supporting both UEFI SecureBoot and Legacy BIOS with Wayland.*

- [ ] **OCI Build Container:** Create the `Containerfile` / `Dockerfile` (Podman/Docker) to bootstrap an `ubuntu:24.04` minimal rootfs without host pollution.
- [ ] **Dual Bootloader Chain:** Configure hybrid bootloaders supporting:
  - UEFI Boot via Canonical's signed `shim` and `grub-efi-amd64-signed`.
  - Legacy PC-BIOS (CSM) via `grub-pc` and MBR boot sector.
- [ ] **Casper Live Boot Engine:** Configure `casper` boot parameters and hooks (inspecting and adapting contest-tested hook patterns from `maratona-linux/maratona-casper`) to:
  - Mount SquashFS modules (`.gsm`) into union layers using in-tree **OverlayFS**.
  - Automatically mount the 3-partition Live USB layout (`GALLOS_BOOT`, `event-data`, `contest-data`).
  - Support the `toram` boot parameter (copy entire OS to RAM for memory-resident disconnected execution).
  - Support the `gallos.config=<path_or_url>` kernel boot parameter for multi-profile selection.
  - Automatically detect and load `/gallos/gallos.toml` when booted inside a **Ventoy** multi-boot drive.
- [ ] **SquashFS Packaging Scripts:** Write `build-squashfs.sh` to package system layers and software modules with `mksquashfs -comp zstd`.
- [ ] **Hybrid ISO Stitched Image:** Write `build-iso.sh` using `xorriso` to generate hybrid bootable `.iso` images.
- [ ] **Wayland Kiosk Desktop Shell:** Assemble the lightweight desktop environment:
  - `labwc` Wayland compositor configured with per-client security isolation.
  - `Waybar` status bar configured with an integrated dropdown application launcher, countdowns, network status, and layout switchers.

---

## Phase 2: Security Lockdown, Anti-Cheat Shield & Resource Hardening (Beta 1)

*Goal: Enforce strict Zero-Trust contest integrity, network air-gapping, and out-of-memory protections.*

- [ ] **Anti-Cheat Enforcement (`nftables`):**
  - [ ] Implement default DROP policy (Zero-Trust)
  - [ ] Static IP / CIDR whitelisting for Judge Servers (`allowed_websites` restricted to IPs for MVP)
  - [ ] Port-locking (block outbound 22, 53 over HTTPS, proxies, UDP hole punching)
- [ ] **Peripheral & USB Lockdown:**
  - Create dynamic `udev` rules to block USB Mass Storage attachment while allowing mice, keyboards, and audio devices.
- [ ] **TTY & Privilege Hardening:**
  - Disable virtual terminal switching (TTY1–6) via kernel/logind parameters.
  - Configure the `contestant` user as unprivileged without `sudo` or polkit administrative rights.
- [ ] **EarlyOOM Guard (`earlyoom -n` + `systembus-notify`):**
  - Configure `earlyoom -n` (D-Bus broadcast) and enable `systembus-notify` user service to display desktop notifications when processes are terminated by EarlyOOM.
  - Protect `gallos-daemon` with `oom_score_adj = -900` while setting browsers to `+500`.

---

## Phase 3: Daemon, Mode State Machine & Dynamic Directives (Beta 2)

*Goal: Implement the real-time configuration engine, multi-mode scheduling, and network sync.*

- [ ] **`gallos-daemon` Core Engine:**
  - Develop a persistent `systemd.service` (Python) capable of maintaining state and open sockets for real-time broadcasts.
  - Implement strict TOML parsing and schema validation against `schema/directives.schema.json` via `taplo`.
- [ ] **Hybrid Config Ingestion & Fallback:**
  - Implement boot sequence logic: attempt to fetch remote `gallos.config_url` with a 5-second timeout; if unreachable, gracefully fall back to local `/boot/gallos/gallos.toml` cache with Plymouth/desktop warnings.
  - Support multi-profile selection via kernel boot arguments.
- [ ] **3-Tier Precedence State Machine:**
  - Implement dynamic scheduling engine: $\text{Contest} \succ \text{Event} \succ \text{Default}$.
  - Transition wallpapers, network firewall rules, and application visibility automatically when contest time-windows start or expire.
- [ ] **Dynamic Hot-Reload Hooks:**
  - Instantaneous wallpaper switching on mode transitions.
  - Dynamic `nftables` rule updates on the fly without rebooting.
- [ ] **Post-Contest Workspace Support:**
  - Re-enable USB mass-storage drivers and provide visual prompts for manual code extraction.
- [ ] **Machine Identity & Team Assignment:**
  - Assign workstation hostnames via DHCP MAC reservations or per-USB `machine.toml` directives.

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
- [ ] **Keyboard Layout Switcher:**
  - Provision and expose Waybar switcher module for configured layouts (`latam`, `us`, `es`, etc.).
- [ ] **Offline Documentation & Translation:**
  - Bundle static HTML documentation packages (`cppreference-doc-en-html`, `python3-doc`, `openjdk-21-doc`).
  - Pre-configure browser bookmarks pointing to `file:///usr/share/doc/`.
  - Bundle lightweight offline dictionary (`GoldenDict` or `stardict`) with EN-ES / EN-PT databases to solve the translation firewall gap without bloating RAM.

---

## Phase 5: Organizer Tooling Suite (RC 1)

*Goal: Build standalone utilities for mass USB preparation, migration, and visual configuration.*

- [ ] **`gallos-convert` (HuronOS Migration CLI):**
  - Parser for legacy `.hdf` configuration formats into canonical `gallos.toml`.
  - Include `--validate` (taplo schema check) and `--diff` CLI flags.
- [ ] **`gallos-flash` (Mass Multi-USB Flashing Tool):**
  - Multi-threaded parallel writer supporting 50+ simultaneous USB targets.
  - Native support for Linux, macOS, and Windows WSL2 via `usbipd-win`.
  - Automatic creation of FAT32 boot, `event-data`, and `contest-data` partitions.
  - Automated per-USB injection of unique `machine.toml` credentials.
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
