# GallosOS

> [!WARNING]
> **Work In Progress - Architectural Phase:** GallosOS is currently in the active design and specification phase. The repository serves as an RFC (Request for Comments) and architectural blueprint. Code implementations, hardware benchmarking, ISO generation tools, and formal academic publications are not yet available.

**GallosOS** is a modern, lightweight, modular, and reproducible Linux Live distribution engineered specifically for competitive programming across **all scenarios**: weekly university club practices, multi-day training camps, and official ICPC / IOI style tournaments.

> *"To create an immutable, secure, and lightweight Live USB that runs reliably on both modern and legacy hardware."*
> — **The GallosOS Core Philosophy**

GallosOS is designed as a **seamless, modern drop-in replacement for [huronOS](https://huronos.org)** across the Mexican competitive programming ecosystem (**[ICPC Gran Premio de México](https://icpc.global/regionals/finder/Mexico)**, **[OMI](https://olimpiadadeinformatica.org.mx/)** — *Olimpiada Mexicana de Informática*, **TCMX** — *Training Camp México*, and university invitationals), while scaling as a world-class, globally adaptable solution for international contests ([ICPC](https://icpc.global/) World Finals/Regionals, [IOI](https://ioinformatics.org/), and [Maratona SBC](https://maratona.sbc.org.br/)).

It synthesizes the foundational architectural strengths of **huronOS** (multi-mode scheduling & layered storage), **[Maratona Linux](https://github.com/maratona-linux/)** (Latin American BOCA judge integration), **[ICPC-Env](https://github.com/icpc-environment/icpc-env)** (standardized toolchains), and the **[IOI-2025 Contestant-VM](https://github.com/ioi-2025/contestant-vm)** (CMS auditing & proctoring), providing a lightweight, tamper-resistant, and white-label operating system **architecturally evaluated against** the entire global competitive programming landscape (including China's **NOI Linux 2.0** and European/Asian ICPC systems).

---

## 🚀 Minimum Viable Product (MVP) Scope

To ensure a rapid, stable release that directly solves the immediate needs of the competitive programming community, the GallosOS MVP is strictly scoped to the following foundational pillars:

1. **Containerized Build Pipeline:** `make build-iso` generates a bootable Ubuntu 24.04 `.iso` via Podman/Docker.
2. **Wayland Kiosk & Ephemeral Storage:** Labwc + Waybar desktop running entirely in RAM (OverlayFS `tmpfs`).
3. **Static Anti-Cheat Firewall:** `nftables` restricted to static judge IPs (Zero-Trust network).
4. **TOML Config Engine:** `gallos-daemon` parsing `gallos.toml` (remote URL or baked-in fallback).

Advanced venue-management features (fleet telemetry, print spooling, proctoring snapshots) are explicitly deferred to post-MVP development (Phase 7).

---

## 🎯 Designed for All Competitive Programming Contexts

```text
+---------------------------------------------------------------------------------------------------+
|  1. Weekly Club Practice & Classes : Immutable USB + semi-free, curated internet access            |
|                                      (AI-result/AI-assistant sites blocked, bookmarks whitelisted) |
|  2. Multi-Day Training Camps       : Automated transitions (Event -> Contest -> Upsolving)        |
|                                      Whitelisted internet suspended during Contest windows         |
|  3. Official Tournaments (ICPC/IOI): Strict Anti-Cheat lockdown, judge-only network, fresh isolation|
|                                      Code exported manually by contestant at contest end          |
+---------------------------------------------------------------------------------------------------+
```

- **Dynamic Online Configuration:** Host a single canonical `gallos.toml` directives file (or legacy `.hdf` migrated via `gallos-convert`) on a **GitHub Gist**, Raw repository, or campus server and update contest times, allowed websites, or bookmarks on the fly *without re-flashing USB drives*.
- **Baked-In Offline Fallback:** Embed configurations directly onto the USB image at burn-time for 100% offline, air-gapped laboratory environments.
- **Workspace Persistence Is Not a Built-In Sync Feature:** GallosOS's filesystem is always immutable and never writes to the USB itself, so saving work outside `Contest` mode happens through one of three paths, none of which GallosOS implements directly: an opt-in `event-data` partition on the contestant's own BYOD drive, a manual USB export when mass storage is unlocked outside a Contest window, or reaching a service like GitHub, GitLab, or Google Drive in the browser — which only works because the organizer's `gallos.toml` whitelist happens to permit that domain as part of the semi-free internet policy, the same way it permits any other bookmarked site. All three are hard-suspended or unavailable the instant a `Contest` window starts (see [`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md) § Mode Hierarchy).

---

## 📚 Architectural & Context Documentation

The repository includes comprehensive context documents and architectural specifications:

- **[`AGENTS.md`](./AGENTS.md):** Guidelines, conventions, and context for AI pair-programming agents and human contributors — the canonical ruleset.
- **[`CLAUDE.md`](./CLAUDE.md):** Claude Code-specific entry point; points back to `AGENTS.md` as the canonical source and adds repo-navigation context for that tool.
- **[`ROADMAP.md`](./ROADMAP.md):** The step-by-step engineering checklist and feature tracker broken down into Alpha, Beta, and RC phases.
- **[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md):** Layered filesystem (OverlayFS + SquashFS), Wayland kiosk desktop (Labwc + Waybar), containerized build engine (Podman/Docker), Windows WSL2 + `usbipd-win` workflows, and VM deployment matrices (`.ova`, `.qcow2`).
- **[`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md):** Canonical `gallos.toml` directives specification, GallosOS Config Builder web/GUI configurator, 3-tier mode hierarchy ($\text{Contest} \succ \text{Event} \succ \text{Default}$), and `gallos-convert` migration tool.
- **[`docs/BUILD_SYSTEM.md`](./docs/BUILD_SYSTEM.md):** The Containerized Build Pipeline (`gallos-builder`), `build.toml` configuration format, and custom ISO generation workflows.
- **[`docs/WAYLAND_DESKTOP.md`](./docs/WAYLAND_DESKTOP.md):** Wayland kiosk desktop specification (Labwc + Waybar + Foot + Mako), keybindings, ergonomic UI modules, and tamper-resistant dotfile architecture.
- **[`docs/HARDWARE_COMPATIBILITY.md`](./docs/HARDWARE_COMPATIBILITY.md):** Firmware support (UEFI SecureBoot & Legacy BIOS), RAM boot (`toram`), and minimal hardware specs.
- **[`docs/ANTI_CHEAT_AND_SECURITY.md`](./docs/ANTI_CHEAT_AND_SECURITY.md):** Threat model, `nftables` kernel packet filtering, Anti-Cheat extension purging (VSCodium / JetBrains), telemetry disabling, USB storage locking, and keyboard layout switching.
- **[`docs/COMPARATIVE_ANALYSIS.md`](./docs/COMPARATIVE_ANALYSIS.md):** Detailed, source-verified comparison matrix evaluating GallosOS against HuronOS, Maratona Linux, ICPC-Env, and IOI Contestant-VM.
- **[`docs/PROVENANCE.md`](./docs/PROVENANCE.md):** Comprehensive ledger tracking all vendored, forked, and adapted third-party code, scripts, and attribution terms.

---

## 🎯 Key Pillars

1. **Ubuntu 24.04 LTS Base, Global Mirrors & UEFI SecureBoot:**
   - Built on Ubuntu 24.04 LTS "Noble Numbat" (Linux Kernel 6.8+): 5-year LTS security updates through 2029+, out-of-the-box driver support for modern Intel/AMD processors, Wi-Fi 6E/7, and Ethernet chipsets common in university labs, and access to Canonical's global package mirrors (build-time) plus GitHub's global CDN (ISO/tool distribution) so organizers building or downloading in Mexico, Brazil, Poland, India, or Japan aren't bottlenecked by a single origin server.
   - Direct `.deb` binary compatibility with Maratona Linux tooling (`maratona-firewall`, `maratona-usuario-icpc`) and official ICPC packages, since both share the Debian/Ubuntu package ecosystem.
   - **Fully supports UEFI SecureBoot out of the box** — unlike huronOS, which patches the out-of-tree AUFS union filesystem into a custom kernel (breaking cryptographic signatures and forcing organizers to manually disable SecureBoot on every contestant laptop), GallosOS pairs Canonical's signed `shim`, the unmodified signed Ubuntu kernel, and in-tree `overlayfs`/`nftables` modules, so a contestant's personal Windows 11 laptop (which mandates SecureBoot) boots the USB immediately with no BIOS setting changes.
   - A hybrid GRUB2/Syslinux bootloader also covers Legacy BIOS (CSM), keeping pre-2015 lab hardware usable in venues that haven't upgraded.

2. **Containerized & Reproducible Build System:**
   - The entire ISO generation pipeline (`debootstrap` → chroot provisioning → strip/optimize → SquashFS + `xorriso` stitch) runs inside an isolated OCI container (Podman / Docker), guaranteeing identical builds on Linux, macOS, and Windows WSL2 without polluting the host OS, plus GitHub Actions CI/CD QA on every release.
   - Three deployment tracks fit different organizer needs: **Track 1** downloads a pre-baked official ISO with zero compilation required; **Track 2** compiles a bespoke base image via the same container for custom kernels or proprietary packages; **Track 3** adds or removes complete software suites at the USB level by dropping/deleting modular `.gsm` SquashFS layers, with no rebuild of the base OS at all (the HuronOS-parity modularity story).
   - Multi-target output — bootable hybrid `.iso`, `.ova` (VirtualBox/VMware), and `.qcow2` (KVM/QEMU) — verified against a QEMU/VirtualBox/VMware/Ventoy testing matrix before physical mass-flashing.
   - Windows-based organizers can build, test, and flash without dual-booting via WSL2 + `usbipd-win` USB passthrough — a secondary convenience path; native Linux remains the primary development target for direct `/dev/sdX` block-device access.

3. **Infrastructure-Agnostic Directives Ingestion (5-Tier Deployment Spectrum):**
   - A `config_url` auto-discovery priority chain resolves where `gallos.toml` comes from — GRUB boot parameter → DHCP Option 235 (deliberately not the commonly-cited 252, which collides with WPAD on real campus networks) → the Venue Controller's `sync-server.conf` → baked-in local fallback — first match wins, and a 5-second remote-fetch timeout with automatic fallback to the cached local config (with a Plymouth + desktop warning) guarantees every machine still boots into a working state if the network is down.
   - Five deployment tiers, each a fully production-ready standalone deployment on its own: **Tier 0** fully air-gapped (baked-in config, zero networking required); **Tier 1** an existing lab router with one added DHCP Option 235 line; **Tier 2** URL-driven sync over any reachable HTTP endpoint — a Gist, campus server, or personal VPS (the HuronOS-style model); **Tier 3** an optional dedicated GallosOS Venue Controller adding fleet monitoring, MAC-based machine identity, printing, and audit aggregation; **Tier 4** externally managed institutional IT infrastructure integrated via standard DHCP/NTP/CUPS protocols. GallosOS never assumes any tier beyond 0 is present, nor that a Venue Controller, internet connectivity, or PXE infrastructure exists.

4. **Trustworthy Time Synchronization:**
   - `chrony` (not legacy `ntpd`) drives the mode scheduler, countdown timers, and audit-log timestamps, converging quickly from a drifted RTC in the first seconds of boot and switching to gradual slewing-only correction once a `Contest` window is active, protecting `make`/`gcc`/`gdb` filesystem timestamps from clock discontinuities.
   - Two complementary scheduling modes cover the full trust spectrum: **absolute ISO 8601 windows** for NTP-synced venues (Tiers 1–4), and a **monotonic-clock relative duration** (`duration_minutes`, immune to wall-clock jumps and RTC corruption) as the primary mechanism for Tier 0 air-gapped deployments where no clock can be trusted at all — `gallos-daemon` falls back to the relative mode automatically if `chrony` reports an unsynchronized clock.
   - A Waybar traffic-light indicator (🟢 NTP-synced / 🟡 local RTC only / 🔴 clock untrusted) tells organizers at a glance which scheduling mode is safe to rely on.

5. **End-to-End Contestant & Organizer Tooling Suite:**
   - **GallosOS Config Builder:** Web & GUI app to visually construct and validate `gallos.toml` directives without manual text editing.
   - **`gallos-convert`:** One-command CLI migration from legacy HuronOS `.hdf` files to canonical TOML.
   - **`gallos-flash`:** Parallel multi-USB mass flashing tool with native WSL2 + `usbipd-win` support.
   - **`gallos-daemon` & `systembus-notify`:** Real-time mode switching, EarlyOOM memory guard, and visual desktop notifications.
   - **`gallos-print`:** CUPS printing pipeline that stamps every printed page (source code, browser `Ctrl+P`, or screen captures) with a tamper-proof team/PC/timestamp/hash header, enforces per-job page quotas, and supports three modes — an existing venue printer, a Controller-hosted USB printer, or fully disabled — essential for in-person ICPC-style team debugging on paper.
   - **`gallos-broadcast`:** An optional, disableable, Ed25519-signed real-time clarification channel from the Venue Controller to contestant desktops (full-screen modal for urgent messages, subtle banner for informational ones) — left completely inert when the judge portal (DOMjudge/BOCA/CMS) already handles clarifications, as in most official ICPC/IOI tournaments.

6. **Multi-Layered Immutable Storage (OverlayFS):**
   - Read-only base SquashFS + modular software packages (`.gsm`).
   - Ephemeral RAM `tmpfs` upper layer ensures a pristine clean state upon reboot; the OS itself never writes to the USB during normal operation.
   - Manual contestant source code export to external USB, cloud sync, or an optional per-contestant `event-data` partition after contest end — `Contest` mode never mounts persistent storage, full stop.

7. **Zero-Leak Anti-Cheat Shield:**
   - Kernel-level packet filter (`nftables`) with a default-DROP policy and IPv6 disabled network-wide, whitelisting only designated judge IPs and local DNS/NTP; DNS-over-HTTPS/TLS and hardcoded IDE telemetry resolvers are dropped outright.
   - Enterprise browser policies add per-path URL allow/block-listing (e.g. for `omegaup.com`) so even a whitelisted domain can't be used to browse outside the active contest arena — `nftables` alone can't see encrypted HTTPS paths.
   - Telemetry-stripped **VSCodium** and **JetBrains Community Editions** (IntelliJ IDEA CE, PyCharm CE) with all AI assistant plugins strictly removed on every boot. (Support for sponsored JetBrains Pro offline license injection is treated as an optional future extension for sponsored championship finals).
   - USB anti-substitution: organizer-issued drives only, optional SquashFS SHA256 attestation reported to the central server at boot, and DHCP/judge-side MAC whitelisting, so a contestant's own modified GallosOS USB can't reach the judge network even if physically plugged in.

8. **Fair & Deterministic Execution Environment:**
   - EarlyOOM — chosen over `oomd`/`systemd-oomd` per HuronOS's own documented field reasoning — proactively `SIGTERM`s the single highest-RAM process before the kernel's late-stage OOM killer can take down the compositor or IDE instead; `nproc`/stack `ulimit`s (256 MB stack matching ICPC/Codeforces judge sandboxes) contain fork bombs and turn runaway recursion into a clean crash instead of a system freeze.
   - CPU turbo/boost disabling and a pinned `performance` frequency governor (with optional HyperThreading sibling-core isolation and `taskset` pinning) remove dynamic-frequency-scaling variance, so a contestant's local benchmark timing on large test cases doesn't randomly swing between machines or runs.

9. **White-Label Branding:**
   - Declarative `[branding]` configuration in `gallos.toml` alongside custom assets (wallpapers, Plymouth boot splash, logos, and bookmarks), allowing institutions to white-label contest environments in seconds.

10. **Process-Isolated Wayland Desktop:**
    - Wayland compositor (Labwc) paired with Waybar (featuring an integrated dropdown menu launcher), eliminating X11 keylogging and screen-snooping vulnerabilities.
    - Hotkey (`Super + Space`, where Super is the Windows key) and status bar-driven keyboard layout switching (`latam`, `us`, `es`, `br-abnt2`, `dvorak`).

11. **Ephemeral & Non-Destructive (BYOD-Friendly):**
    - Booting from a Live USB solves infrastructure compatibility problems by leaving the host computer's hard drive untouched. This makes it safe and viable for both highly controlled university labs and low-resource environments.
    - **Contextualized for Latin American Realities:** We acknowledge the disparity in computational and network infrastructure across the region. Having an offline-capable system that runs entirely from RAM ensures that events can happen successfully even in environments with scarce or practically non-existent connectivity. Legacy Broadcom Wi-Fi chips common in older BYOD laptops get open-source firmware support where legally redistributable, with a documented help-desk fallback (USB Ethernet/Wi-Fi dongles) for hardware GallosOS can't legally ship firmware for.
    - Ideal for university programming clubs: students can bring their own personal laptops (BYOD, which typically run Windows). The official recommendation is to boot GallosOS during club sessions so students get accustomed to the exact same distraction-free, standardized environment used in official contests, building familiarity without permanently altering their personal OS. Cloud-sync credentials (OAuth device flow, session-only `ssh-agent`, RAM-cached git credential helper) never touch disk and are wiped on every reboot, avoiding credential leakage between teams sharing a machine.

12. **English-First by Default & Built-in Translation Support:**
    - Competitive programming is an inherently international ecosystem where problem statements, compiler warnings, official documentation, and judge platforms are universally standardized in English.
    - GallosOS enforces an English-language desktop and terminal environment by default. This design choice explicitly mirrors global contest realities, encouraging language immersion and preparing contestants for international tournaments.
    - Acknowledging the learning curve for non-native speakers (especially within the Latin American ecosystem during `Event` and Training Camp modes), GallosOS explicitly integrates offline dictionary tools and allows Organizers to selectively whitelist online translation services via `gallos.toml`.

13. **Optional Proctoring, Auditing & Fleet Telemetry (Tier 3, Venue Controller Only):**
    - Opt-in per `[contest.audit]` in `gallos.toml`: periodic Wayland-safe screen capture (`grim`/`wlr-screencopy`, root-privileged and invisible to unprivileged apps), incremental code backups every $N$ seconds for dispute resolution and crash recovery, and keystroke/window-focus forensics reserved mainly for IOI/Olympiad arbitration (disabled by default for ICPC and university camps).
    - Because contestant workstations run entirely in ephemeral RAM, the Venue Controller is the only persistent sink for this telemetry — exported as a single `gallos-audit-YYYYMMDD.tar.gz` for jury review. None of this exists or is collected unless an organizer explicitly deploys a Venue Controller; the default public ISO never phones home.

14. **Dynamic 3-Tier Mode Hierarchy:**
    - Building upon the foundational design of huronOS, the core scheduling engine dynamically transitions the OS state between three strict modes: **Contest $\succ$ Event $\succ$ Default**.
    - During a `Contest` window, the system executes a **Clean State Wipe** (kills the session, purges `/home/contestant/`, restores a pristine skeleton, restarts fresh) before enforcing a strict Zero-Trust network firewall, updated desktop branding, and blocked USB code extraction. During an `Event` window (e.g., a multi-day training camp), it allows relaxed browsing and persistent workspaces, intelligently hiding previous work the moment a contest begins.

---

## 📖 Terminology

The following terms are used consistently across all GallosOS documentation:

| Term | Definition |
| :--- | :--- |
| **Contestant** | A programmer actively competing or practicing at a GallosOS workstation. The OS user account is always the fixed, unprivileged `contestant` system user. The canonical term throughout GallosOS documentation; avoid *participant* except when quoting an external source verbatim. |
| **Organizer** | The person or committee responsible for configuring and deploying GallosOS for an event. Manages `gallos.toml`, runs `gallos-flash`, and optionally operates the Venue Controller. Synonymous with *contest director* or *jury*. |
| **Venue Controller** | An optional dedicated machine — booted from the same GallosOS USB/ISO as contestant workstations, just started in Server Mode instead — that runs on the contest LAN to provide centralized fleet monitoring, DHCP/NTP, CUPS print spooling, MAC-to-team identity mapping, and audit log aggregation. Only required for Tier 3 deployments — GallosOS works without one. |
| **Judge Server** | The external competitive programming judge system (e.g. BOCA, DOMjudge, PC², CMS, omegaUp, Codeforces) running on a separate dedicated machine managed by the contest organizer. GallosOS **never** hosts the judge — it connects to it. |

---

## 📁 Repository Layout

```text
GallosOS/
├── AGENTS.md                  # Project rules for AI agents and human contributors
├── CLAUDE.md                  # Claude Code entry point; defers to AGENTS.md as canonical
├── ROADMAP.md                 # Development phases and feature checklist
├── README.md                  # Project overview and quickstart
├── LICENSE                    # GNU General Public License v2.0 or later
├── docs/                      # Architectural & design specifications
│   ├── ARCHITECTURE.md        # System design, Wayland, OverlayFS, Build & VM testing
│   ├── CONFIG_SPEC.md         # Canonical TOML directives, GallosOS Config Builder & mode hierarchy
│   ├── BUILD_SYSTEM.md        # Containerized Build Pipeline & build.toml specification
│   ├── WAYLAND_DESKTOP.md     # Wayland kiosk desktop spec, Labwc/Waybar dotfiles & UX
│   ├── HARDWARE_COMPATIBILITY.md # Firmware support (UEFI SecureBoot & Legacy BIOS), RAM specs
│   ├── ANTI_CHEAT_AND_SECURITY.md# Firewall, Anti-Cheat protection, telemetry & USB lockdown
│   ├── COMPARATIVE_ANALYSIS.md# In-depth comparison with existing contest distributions
│   └── PROVENANCE.md          # Third-party code, vendored assets & attribution ledger
├── examples/                  # Production-ready gallos.toml configuration profiles
│   ├── icpc-onsite.toml       # ICPC Regional / World Finals (BOCA/DOMjudge, GCC 14, Java 21)
│   ├── maratona-sbc.toml      # Maratona SBC / South America Regional (BOCA, ABNT2, GCC 14)
│   ├── icpc-online-exam.toml  # ICPC Preliminary Online (CodeChef Exam Mode lockdown)
│   ├── codeforces-training.toml # Camp & practice mode (Codeforces, AtCoder, Clang, Rust)
│   ├── ioi-cms.toml           # IOI / National Olympiad (CMS Judge, C++23 focus)
│   └── omegaup-omi.toml       # OMI & Latin American Olympiads (omegaUp platform)
└── schema/                    # Directives validation schemas
    └── directives.schema.json # JSON Schema for gallos.toml (taplo integration)
```

---

## 📜 License & Acknowledgements

**GallosOS** is free software licensed under the **[GNU General Public License v2.0 or later (GPL-2.0-or-later)](./LICENSE)**.

### Upstream Inspiration & Acknowledgements

GallosOS builds upon foundational research, packaging standards, and operational workflows pioneered by the competitive programming community:

- **[huronOS](https://huronos.org)** (`GPL-2.0`): Modular SquashFS architecture, dynamic contest mode state-machine transitions, and `.hdf` synchronization.
- **[Maratona Linux](https://maratona.ime.usp.br/)** (`GPL-2.0`): ICPC Latin America packaging, BOCA judge integration, and firewall filtering concepts.
- **[ICPC-Env](https://github.com/icpc-environment/icpc-env)**: Standardized language toolchains, proxy-based network filtering, and offline DevDocs setups. Dormant since October 2024; its primary maintainer ([`ubergeek42`](https://github.com/ubergeek42)) is also a contributor to [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible), the actively-maintained ICPC World Finals/NAC SysOps playbook set that GallosOS treats as the more current reference for several of the same subsystems (printing, keystroke/window forensics, workspace backup — see [`docs/PROVENANCE.md`](./docs/PROVENANCE.md)).
- **[IOI Contestant-VM](https://github.com/ioi-2025/contestant-vm)**: Official IOI environment standards, minimal desktop configuration, and automated VM provisioning.
