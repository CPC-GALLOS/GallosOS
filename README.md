# GallosOS

> [!WARNING]
> **Work In Progress:** The Phase 1–3 implementation has passed a complete Live-image QEMU test of the signed ISO, host-visible event storage, transition failure recovery, and a Contest-to-Default retry sequence. Physical venue hardware and contestant desktop workflows still need acceptance testing before deployment. Organizer tooling (Phase 5) has not been started. **Hardware benchmarking, physical lab trials, and formal academic publications have not occurred** — see `ROADMAP.md` for the exact status.

**GallosOS** is a modern, lightweight, modular, and reproducible Linux Live distribution engineered specifically for competitive programming across **all scenarios**: weekly university club practices, multi-day training camps, and official ICPC / IOI style tournaments.

> *"To create an immutable, secure, and lightweight Live USB that runs reliably on both modern and legacy hardware."*
> — **The GallosOS Core Philosophy**

GallosOS is designed as a **seamless, modern drop-in replacement for [huronOS](https://huronos.org)** across the Mexican competitive programming ecosystem (**[ICPC Gran Premio de México](https://icpc.global/regionals/finder/Mexico)**, **[OMI](https://olimpiadadeinformatica.org.mx/)** — *Olimpiada Mexicana de Informática*, **TCMX** — *Training Camp México*, and university invitationals), while scaling as a world-class, globally adaptable solution for international contests ([ICPC](https://icpc.global/) World Finals/Regionals, [IOI](https://ioinformatics.org/), and [Maratona SBC](https://maratona.sbc.org.br/)).

It originated from the **CPC-GALLOS** competitive programming club at Universidad Autónoma de Aguascalientes (UAA). While configuring and deploying huronOS for official ICPC Gran Premio de México dates in [`CPC-GALLOS/icpc-gpm-uaa-huronos`](https://github.com/CPC-GALLOS/icpc-gpm-uaa-huronos), the team encountered systemic hardware and network roadblocks—including kernel 6.0 driver obsolescence on modern Intel/NVIDIA silicon requiring unaccelerated fbdev/software-rendering fallbacks, ConnMan failures on campus WPA-Enterprise Wi-Fi (`RIUAA`/`eduroam`), and fragile offline extension grafting. These practical contest difficulties directly sparked the architectural creation of GallosOS as a ground-up, modern Linux distribution.

It synthesizes the foundational architectural strengths of **huronOS** (multi-mode scheduling & layered storage), **[Maratona Linux](https://github.com/maratona-linux/)** (Latin American BOCA judge integration), **[ICPC-Env](https://github.com/icpc-environment/icpc-env)** (standardized toolchains), and the **[IOI-2025 Contestant-VM](https://github.com/ioi-2025/contestant-vm)** (CMS auditing & proctoring), providing a lightweight, tamper-resistant, and white-label operating system **architecturally evaluated against** the entire global competitive programming landscape (including China's **NOI Linux 2.0** and European/Asian ICPC systems).

---

## 🚀 Minimum Viable Product (MVP) Scope

The release target serves **developers** with a repeatable local programming
workspace, **contestants** with the same tools for practice and competition,
and **Organizers** with one ISO whose policy can be selected at boot. Its
no-configuration baseline is GallosOS-branded, opens public-judge practice,
and supports informal contests. Strict official contests need an Organizer
profile naming their judge and time window.

The selected release toolchains are GCC (C/C++), Clang (C/C++), OpenJDK
(Java), Python/PyPy, Rust, and Kotlin, alongside Geany, terminal editors,
Firefox, and VSCodium. The build writes exact installed package versions to
`/usr/share/gallos/toolchains.tsv`. This is a curated core, not language
parity with every Codeforces, HackerRank, LeetCode, or omegaUp runtime.

The anti-AI website and search-results policy, including review of web relays
such as translated-page and browser-proxy services, is a separate release
requirement. The current open practice baseline does not enforce that policy.

To ensure a rapid, stable release that directly solves the immediate needs of the competitive programming community, the GallosOS MVP is strictly scoped to the following foundational pillars:

1. **Containerized Build Pipeline:** `cd build && make iso` generates a bootable Ubuntu 24.04 `.iso` via Podman/Docker.
2. **Wayland Kiosk & Ephemeral Storage:** Labwc + Waybar desktop running entirely in RAM (OverlayFS `tmpfs`).
3. **Static Anti-Cheat Firewall:** `nftables` restricted to static judge IPs (Zero-Trust network).
4. **TOML Config Engine:** `gallosd` loads Organizer policy from local TOML; an authorized Organizer can edit the root-only emergency copy during a contest and reload it with `gallosctl`.

Advanced venue-management features (fleet telemetry, print spooling, proctoring snapshots) are explicitly deferred to post-MVP development (Phase 7).

---

## 🛠️ Prerequisites & Host Setup

To build, test, and develop GallosOS locally, your host machine requires:

| Category | Tools / Packages | Purpose |
| :--- | :--- | :--- |
| **Container Engine** *(Required for ISO build)* | `podman` *(recommended)* or `docker` | Containerized pipeline build (`cd build && make iso`). |
| **Virtualization & Emulation** *(Testing)* | `qemu-system-x86`, `edk2-ovmf`, `virt-manager`, `libvirt` | Booting the Live ISO (`build/scripts/test-iso-qemu.sh`) in BIOS or UEFI mode. |
| **Disk & Image Utilities** | `parted`, `mtools`, `dosfstools`, `e2fsprogs`, `xorriso` | Generating synthetic USB test images and extracting `toram` boot images. |
| **Python & QA Suite** | `python3` (>=3.10), `uv` (recommended) or `pip`, `ruff`, `pytest`, `shellcheck` | Running `./scripts/check.sh` and local unit test suites. |

### Installing Prerequisites

#### Fedora / RHEL
```bash
sudo dnf install -y podman qemu-kvm edk2-ovmf virt-manager libvirt \
                    parted mtools dosfstools e2fsprogs xorriso shellcheck
```

For Python QA tools, install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) and create a project-local environment:

```bash
uv venv
uv pip install --python .venv/bin/python ruff pytest jsonschema
source .venv/bin/activate
```

Prefer `pip`? Use the equivalent virtual environment and install command:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ruff pytest jsonschema
```

#### Debian / Ubuntu
```bash
sudo apt update
sudo apt install -y podman qemu-system-x86 ovmf virt-manager libvirt-daemon-system \
                    parted mtools dosfstools e2fsprogs xorriso shellcheck python3-venv
```

For Python QA tools, install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) and create a project-local environment:

```bash
uv venv
uv pip install --python .venv/bin/python ruff pytest jsonschema
source .venv/bin/activate
```

Prefer `pip`? Use the equivalent virtual environment and install command:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ruff pytest jsonschema
```

---

## 🎯 Designed for All Competitive Programming Contexts

```text
+---------------------------------------------------------------------------------------------------+
|  1. Weekly Club Practice & Classes : Immutable USB + open internet; anti-AI policy pending          |
|                                      CPC-GALLOS identity is an opt-in runtime profile               |
|  2. Multi-Day Training Camps       : Automated transitions (Event -> Contest -> Upsolving)        |
|                                      Whitelisted internet suspended during Contest windows         |
|  3. Official Tournaments (ICPC/IOI): Strict Anti-Cheat lockdown, judge-only network, fresh isolation|
|                                      Code exported manually by contestant at contest end          |
+---------------------------------------------------------------------------------------------------+
```

- **Local TOML Configuration:** Store the Organizer policy on the approved boot medium. During a contest, an authorized Organizer can make a last-minute correction in `/etc/gallos/gallos.toml` and run `gallosctl reload`; invalid TOML leaves the active policy in place and reports an error.
- **Baked-In Practice Baseline:** The ISO includes a neutral, open practice profile when no Organizer policy is supplied. Installed tools remain usable without internet.
- **Optional Local Workspace:** Outside `Contest`, the host-mounted `event-data` partition exposes `/media/event-data/contestant` for files the contestant intentionally saves. Contest entry must unmount it before releasing the fresh session. Manual USB export and organizer-allowed external services are separate options (see [`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md) § Mode Hierarchy).

---

## 📚 Architectural & Context Documentation

The repository includes comprehensive context documents and architectural specifications:

- **[`AGENTS.md`](./AGENTS.md):** Guidelines, conventions, and context for AI pair-programming agents and human contributors — the canonical ruleset.
- **[`ROADMAP.md`](./ROADMAP.md):** The step-by-step engineering checklist and feature tracker broken down into Alpha, Beta, and RC phases.
- **[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md):** Layered filesystem (OverlayFS + SquashFS), Wayland kiosk desktop (Labwc + Waybar), containerized build engine (Podman/Docker), Windows WSL2 + `usbipd-win` workflows, and VM deployment matrices (`.ova`, `.qcow2`).
- **[`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md):** Canonical `gallos.toml` directives specification, GallosOS Config Builder web/GUI configurator, 3-tier mode hierarchy ($\text{Contest} \succ \text{Event} \succ \text{Default}$), and `gallos-convert` migration tool.
- **[`docs/BUILD_SYSTEM.md`](./docs/BUILD_SYSTEM.md):** The Containerized Build Pipeline (`gallos-builder`), `build.toml` configuration format, and custom ISO generation workflows.
- **[`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md):** How to lint, format, and test `gallosd` (`daemon/`) locally with `./scripts/check.sh`, install the pre-commit hooks, and what the GitHub Actions CI gate checks.
- **[`docs/WAYLAND_DESKTOP.md`](./docs/WAYLAND_DESKTOP.md):** Wayland kiosk desktop specification (Labwc + Waybar + Foot + Mako), keybindings, ergonomic UI modules, and tamper-resistant dotfile architecture.
- **[`docs/BOOT_BRANDING.md`](./docs/BOOT_BRANDING.md):** Design (not yet implemented, targets Phase 4) for a custom Plymouth boot splash and GRUB boot menu theme, plus an inventory of remaining stock-Ubuntu branding to remove.
- **[`docs/ROOT_ACCESS.md`](./docs/ROOT_ACCESS.md):** Local root recovery (`su` during a normal session, or a password-protected tty1 prompt after transition failure). It requires a locally declared password hash.
- **[`docs/HARDWARE_COMPATIBILITY.md`](./docs/HARDWARE_COMPATIBILITY.md):** Firmware support (UEFI SecureBoot & Legacy BIOS), RAM boot (`toram`), and minimal hardware specs.
- **[`docs/ANTI_CHEAT_AND_SECURITY.md`](./docs/ANTI_CHEAT_AND_SECURITY.md):** Threat model, `nftables` kernel packet filtering, Anti-Cheat extension purging (VSCodium / JetBrains), telemetry disabling, USB storage locking, and keyboard layout switching.
- **[`docs/COMPARATIVE_ANALYSIS.md`](./docs/COMPARATIVE_ANALYSIS.md):** Detailed, source-verified comparison matrix evaluating GallosOS against HuronOS, Maratona Linux, ICPC-Env, and IOI Contestant-VM.
- **[`docs/PROVENANCE.md`](./docs/PROVENANCE.md):** Comprehensive ledger tracking all vendored, forked, and adapted third-party code, scripts, and attribution terms.

---

## 🎯 Key Pillars

1. **Ubuntu 24.04 LTS Base, Global Mirrors & UEFI SecureBoot:**
   - Built on Ubuntu 24.04 LTS "Noble Numbat" (Linux Kernel 6.8+): 5-year LTS security updates through 2029+, out-of-the-box driver support for modern Intel/AMD processors, Wi-Fi 6E/7, and Ethernet chipsets common in university labs, and access to Canonical's global package mirrors (build-time) plus GitHub's global CDN and the official Google Drive mirror (`cpc.gallos@gmail.com`) for direct full-sized ISO distribution so organizers building or downloading in Mexico, Brazil, Poland, India, or Japan aren't bottlenecked by a single origin server.
   - Direct `.deb` binary compatibility with Maratona Linux tooling (`maratona-firewall`, `maratona-usuario-icpc`) and official ICPC packages, since both share the Debian/Ubuntu package ecosystem.
   - The ISO builder assembles Ubuntu's signed shim, GRUB, and kernel and verifies the latter two against Canonical's certificate. The complete GallosOS Live image reached `multi-user.target` in QEMU with Secure Boot enforced, including a `toram` boot. Physical hardware still requires validation before compatibility can be claimed for a venue.
   - A GRUB BIOS El Torito image and hybrid MBR provide a Legacy BIOS boot path; older lab machines still need venue testing.
    - **Configurable base OS version (`build.toml`):** Ubuntu 24.04 LTS is the only version the GallosOS maintainer builds and tests against, and remains the default for every official release. Organizers needing a different target — an older LTS (`ubuntu-22.04-minimal`) for legacy hardware, a newer LTS (`ubuntu-26.04-minimal`), or an interim non-LTS release for bleeding-edge hardware support — can set `base_os` in `build.toml` (e.g. `build/profiles/universal.build.toml`) and compile a bespoke image via Track 2 (see `docs/BUILD_SYSTEM.md` § 2). These alternate targets are architecturally compatible but **not validated by the upstream maintainer** — treat them as community-supported.
    - **Optional proprietary GPU drivers (`drivers/nvidia-proprietary` `.gsm` module):** For venues with discrete NVIDIA GPUs and no integrated-graphics fallback (e.g. an Intel CPU with no iGPU paired with an RTX-series card), organizers can opt into a proprietary NVIDIA driver module for full graphics acceleration and video playback. This is explicit opt-in — it taints the kernel and requires a one-time, per-machine MOK enrollment to keep SecureBoot enforced (see `docs/HARDWARE_COMPATIBILITY.md` § 1.2). The default image's unmodified-kernel, never-tainted guarantee is unaffected unless a venue turns this on.

2. **Containerized & Reproducible Build System:**
   - The entire ISO generation pipeline (`debootstrap` → chroot provisioning → strip/optimize → SquashFS + `xorriso` stitch) runs inside an isolated OCI container (Podman / Docker), guaranteeing identical builds on Linux, macOS, and Windows WSL2 without polluting the host OS, plus GitHub Actions CI/CD QA on every release.
   - Three deployment tracks fit different organizer needs: **Track 1** downloads a pre-baked official ISO with zero compilation required (hosted on GitHub Releases CDN for split/standard releases, and mirrored via Google Drive on `cpc.gallos@gmail.com` for direct single-file monolithic downloads exceeding GitHub's 2 GB asset limit); **Track 2** compiles a bespoke base image via the same container for custom kernels or proprietary packages; **Track 3** adds or removes complete software suites at the USB level by dropping/deleting modular `.gsm` SquashFS layers, with no rebuild of the base OS at all (the HuronOS-parity modularity story).
   - Multi-target output — bootable hybrid `.iso`, `.ova` (VirtualBox/VMware), and `.qcow2` (KVM/QEMU) — verified against a QEMU/VirtualBox/VMware/Ventoy testing matrix before physical mass-flashing.
   - Windows-based organizers can build, test, and flash without dual-booting via WSL2 + `usbipd-win` USB passthrough — a secondary convenience path; native Linux remains the primary development target for direct `/dev/sdX` block-device access.

3. **Infrastructure-Agnostic Directives Ingestion (5-Tier Deployment Spectrum):**
   - The runtime loads local TOML policy: root-only `/etc/gallos/gallos.toml`, approved boot-medium policy, one unique named profile, then the bundled baseline. Boot arguments, DHCP options, remote URLs, and arbitrary attached disks do not supply policy. An Organizer can edit the root-only override during Contest and reload through `gallosctl`.
   - Deployment tiers describe future infrastructure options. DHCP-driven config distribution, remote sync, fleet monitoring, and the Venue Controller are architectural designs, not implemented runtime features.

4. **Trustworthy Time Synchronization:**
   - `chrony` (not legacy `ntpd`) drives the mode scheduler, countdown timers, and audit-log timestamps, converging quickly from a drifted RTC in the first seconds of boot and switching to gradual slewing-only correction once a `Contest` window is active, protecting `make`/`gcc`/`gdb` filesystem timestamps from clock discontinuities.
   - Two complementary scheduling modes cover the full trust spectrum: **absolute ISO 8601 windows** for NTP-synced venues (Tiers 1–4), and a **monotonic-clock relative duration** (`duration_minutes`, immune to wall-clock jumps and RTC corruption) as the primary mechanism for Tier 0 air-gapped deployments where no clock can be trusted at all — `gallosd` falls back to the relative mode automatically if `chrony` reports an unsynchronized clock.
   - A Waybar traffic-light indicator (🟢 NTP-synced / 🟡 local RTC only / 🔴 clock untrusted) tells organizers at a glance which scheduling mode is safe to rely on.

5. **End-to-End Contestant & Organizer Tooling Suite:**
   - **GallosOS Config Builder:** Web & GUI app to visually construct and validate `gallos.toml` directives without manual text editing.
   - **`gallos-convert`:** One-command CLI migration from legacy HuronOS `.hdf` files to canonical TOML.
   - **`gallos-flash`:** Parallel multi-USB mass flashing tool with native WSL2 + `usbipd-win` support.
   - **`gallosd` & `systembus-notify`:** Real-time mode switching, EarlyOOM memory guard, and visual desktop notifications.
   - **`gallos-print`:** CUPS printing pipeline that stamps every printed page (source code, browser `Ctrl+P`, or screen captures) with a tamper-proof team/PC/timestamp/hash header, enforces per-job page quotas, and supports three modes — an existing venue printer, a Controller-hosted USB printer, or fully disabled — essential for in-person ICPC-style team debugging on paper.
   - **`gallos-broadcast`:** An optional, disableable, Ed25519-signed real-time clarification channel from the Venue Controller to contestant desktops (full-screen modal for urgent messages, subtle banner for informational ones) — left completely inert when the judge portal (DOMjudge/BOCA/CMS) already handles clarifications, as in most official ICPC/IOI tournaments.

6. **Multi-Layered Immutable Storage (OverlayFS):**
   - Read-only base SquashFS + modular software packages (`.gsm`).
   - Ephemeral RAM `tmpfs` upper layer ensures a pristine clean state upon reboot; the OS itself never writes to the USB during normal operation.
   - Manual contestant source code export to external USB, manual export to a whitelisted external workspace (GitHub, GitLab, Google Drive), or an optional per-contestant `event-data` partition after contest end — `Contest` mode never mounts persistent storage, full stop.

7. **Zero-Leak Anti-Cheat Shield:**
   - Kernel-level packet filter (`nftables`) with a default-DROP policy and IPv6 disabled network-wide, whitelisting only designated judge IPs and local DNS/NTP; DNS-over-HTTPS/TLS and hardcoded IDE telemetry resolvers are dropped outright.
   - Enterprise browser policies add per-path URL allow/block-listing (e.g. for `omegaup.com`) so even a whitelisted domain can't be used to browse outside the active contest arena — `nftables` alone can't see encrypted HTTPS paths.
   - The build targets VSCodium with telemetry and automatic updates disabled in the contestant defaults. JetBrains IDE packaging and AI-plugin removal remain future work.
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
    - Ideal for university programming clubs: students can bring their own personal laptops (BYOD, which typically run Windows). The official recommendation is to boot GallosOS during club sessions so students get accustomed to the exact same distraction-free, standardized environment used in official contests, building familiarity without permanently altering their personal OS. External-workspace credentials (OAuth device flow, session-only `ssh-agent`, RAM-cached git credential helper) never touch disk and are wiped on every reboot, avoiding credential leakage between teams sharing a machine.

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
├── ROADMAP.md                 # Development phases and feature checklist
├── README.md                  # Project overview and quickstart
├── LICENSE                    # GNU General Public License v2.0 or later
├── pyproject.toml             # Ruff & Pytest configuration for daemon/
├── .pre-commit-config.yaml    # Local git hooks (Conventional Commits, Ruff, ShellCheck, hygiene)
├── .github/
│   └── workflows/ci.yml       # GitHub Actions: PR title & commit checks, lint, format, tests, shellcheck, TOML
├── build/                     # Containerized ISO build pipeline (Podman / Docker)
│   ├── profiles/              # Declarative build manifests (*.build.toml)
│   │   ├── README.md          # Build profile catalog and Track 2 customization guide
│   │   └── universal.build.toml # Canonical MVP base image recipe (gallosos-universal-amd64.iso)
│   └── scripts/               # Staged build scripts (bootstrap, provision, harden, optimize)
├── daemon/                    # gallosd: runtime mode/config/firewall daemon (Python)
│   ├── src/                   # main.py, config.py, state_machine.py, firewall.py, etc.
│   └── tests/                 # Pytest unit test suite (test_*.py, one per src module)
├── scripts/                   # Repo-local dev tooling (not part of the ISO build pipeline)
│   ├── check.sh               # Single pre-flight command: ruff + pytest + shellcheck + TOML + commits
│   ├── check_commits.py       # Conventional Commits validator (local, git hook, and CI)
│   └── validate_toml.py       # Syntax-only TOML fallback validator used by check.sh
├── docs/                      # Architectural & design specifications
│   ├── ARCHITECTURE.md        # System design, Wayland, OverlayFS, Build & VM testing
│   ├── CONFIG_SPEC.md         # Canonical TOML directives, GallosOS Config Builder & mode hierarchy
│   ├── BUILD_SYSTEM.md        # Containerized Build Pipeline & build.toml specification
│   ├── DEVELOPMENT.md         # Linting, testing & CI workflow for gallosd (daemon/)
│   ├── WAYLAND_DESKTOP.md     # Wayland kiosk desktop spec, Labwc/Waybar dotfiles & UX
│   ├── HARDWARE_COMPATIBILITY.md # Firmware support (UEFI SecureBoot & Legacy BIOS), RAM specs
│   ├── ANTI_CHEAT_AND_SECURITY.md# Firewall, Anti-Cheat protection, telemetry & USB lockdown
│   ├── COMPARATIVE_ANALYSIS.md# In-depth comparison with existing contest distributions
│   └── PROVENANCE.md          # Third-party code, vendored assets & attribution ledger
├── examples/                  # Organizer gallos.toml profiles and policy examples
│   ├── README.md              # Profile catalog, gallos.toml vs machine.toml, deployment & config precedence
│   ├── neutral.gallos.toml       # GallosOS-branded ISO fallback
│   ├── club.gallos.toml          # CPC-GALLOS club practice with open internet
│   ├── training.gallos.toml      # Reviewed multi-judge training allowlist
│   ├── icpc-online-exam.gallos.toml  # ICPC Preliminary Online (CodeChef Exam Mode lockdown)
│   ├── exam.gallos.toml              # Moodle policy test; not for live exams
│   ├── icpc-onsite.gallos.toml       # ICPC Regional / World Finals (BOCA/DOMjudge, GCC 14, Java 21)
│   ├── ioi-cms.gallos.toml           # IOI / National Olympiad (CMS Judge, C++23 focus)
│   ├── maratona-sbc.gallos.toml      # Maratona SBC / South America Regional (BOCA, ABNT2, GCC 14)
│   └── omegaup-omi.gallos.toml       # OMI & Latin American Olympiads (omegaUp platform)
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
