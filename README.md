# GallosOS

> [!WARNING]
> **Work In Progress:** Historical Live-image QEMU runs covered the signed ISO, host-visible event storage, transition failure recovery, and a Contest-to-Default retry sequence. Implementation completion and release acceptance are tracked separately in [`ROADMAP.md`](./ROADMAP.md): `[x]` denotes implementation, while acceptance results require an identified image and evidence. Physical venue hardware and contestant desktop workflows still need acceptance testing before deployment. Organizer tooling (Phase 5) has not been started. **Hardware benchmarking, physical lab trials, and formal academic publications have not occurred.**

**GallosOS** is a work-in-progress Linux Live distribution designed for competitive programming, from weekly university practice and training camps to official ICPC / IOI-style tournaments. The current implementation and release-acceptance status are tracked separately in the roadmap below.

GallosOS aims to provide a modern alternative to [huronOS](https://huronos.org) for the Mexican competitive programming ecosystem (**[ICPC Gran Premio de México](https://icpc.global/regionals/finder/Mexico)**, **[OMI](https://olimpiadadeinformatica.org.mx/)** — *Olimpiada Mexicana de Informática*, **TCMX** — *Training Camp México*, and university invitationals), with a design intended to adapt to international contests ([ICPC](https://icpc.global/) World Finals/Regionals, [IOI](https://ioinformatics.org/), and [Maratona SBC](https://maratona.sbc.org.br/)). Deployment readiness remains subject to the acceptance gates in [`ROADMAP.md`](./ROADMAP.md).

It originated from the **CPC-GALLOS** competitive programming club at Universidad Autónoma de Aguascalientes (UAA). While configuring and deploying huronOS for official ICPC Gran Premio de México dates in [`CPC-GALLOS/icpc-gpm-uaa-huronos`](https://github.com/CPC-GALLOS/icpc-gpm-uaa-huronos), the team encountered systemic hardware and network roadblocks—including kernel 6.0 driver obsolescence on modern Intel/NVIDIA silicon requiring unaccelerated fbdev/software-rendering fallbacks, ConnMan failures on campus WPA-Enterprise Wi-Fi (`RIUAA`/`eduroam`), and fragile offline extension grafting. These practical contest difficulties directly sparked the architectural creation of GallosOS as a ground-up, modern Linux distribution.

Its design draws on reference projects including **huronOS** (multi-mode scheduling and layered storage), **[Maratona Linux](https://github.com/maratona-linux/)**, **[ICPC-Env](https://github.com/icpc-environment/icpc-env)**, and the **[IOI-2025 Contestant-VM](https://github.com/ioi-2025/contestant-vm)**. These references do not imply that their judge integrations, auditing, or proctoring systems are implemented in GallosOS. See [`docs/COMPARATIVE_ANALYSIS.md`](./docs/COMPARATIVE_ANALYSIS.md) for the source-based architectural comparison.

---

## 🚀 Minimum Viable Product (MVP) Scope

The release target serves **developers** with a repeatable local programming
workspace, **contestants** with a selected toolchain for practice and
competition, and **Organizers** with an ISO that can load approved policy at
boot. The neutral baseline is designed for open public-judge practice; formal
Contest restrictions require an Organizer policy. Release acceptance for
these workflows remains open in [`ROADMAP.md`](./ROADMAP.md#release-acceptance).

The selected release toolchains are GCC (C/C++), Clang (C/C++), OpenJDK
(Java), Python/PyPy, Rust, and Kotlin, alongside Geany, terminal editors,
Firefox, and VSCodium. The build writes exact installed package versions to
`/usr/share/gallos/toolchains.tsv`. This is a curated core, not language
parity with every Codeforces, HackerRank, LeetCode, or omegaUp runtime.

The anti-AI website and search-results policy, including review of web relays
such as translated-page and browser-proxy services, is a separate release
requirement. The current open practice baseline does not enforce that policy.

The current MVP implementation scope is organized around these foundational areas; release acceptance remains tracked separately:

1. **Containerized Build Pipeline:** Export `GALLOS_GRUB_PASSWORD_HASH` as described in [the build guide](./docs/BUILD_SYSTEM.md), then run `cd build && make iso` to generate a bootable Ubuntu 24.04 `.iso` via Podman/Docker.
2. **Wayland Session & Ephemeral Writable Layer:** Labwc + Waybar are provisioned for the Live session. The writable OverlayFS layer uses `tmpfs`; this does not mean the full image is copied into RAM unless `toram` is selected.
3. **Policy-Scoped Security:** Restricted Organizer policies use `nftables`, the local web proxy, and device controls; the neutral ISO permits open practice. Enforcement requires live-image acceptance.
4. **TOML Config Engine:** `gallosd` loads Organizer policy from local TOML; an authorized Organizer can edit the root-only emergency copy during a contest and reload it with `gallosctl`.

Workstation printing is planned in Phase 4. Central venue services, fleet telemetry, and proctoring snapshots are planned in Phase 7. Neither is required for standalone practice.

---

## 🛠️ Prerequisites & Host Setup

> [!TIP]
> **Quickstart with Dev Containers & GitHub Codespaces:**
> Use the [Dev Container](./.devcontainer/README.md) for an Ubuntu 24.04 workspace with Python 3.12, `uv`, Python QA tools, ShellCheck, Docker-in-Docker for Live ISO builds, and Git hooks. Local use with VS Code, Cursor, or DevPod requires a working container runtime; GitHub Codespaces supplies its own. See the [setup instructions](./.devcontainer/README.md#quickstart) and [development guide](./docs/DEVELOPMENT.md#11-dev-container--github-codespaces).

For host-native development and testing, install the tools below as needed:

| Category | Tools / Packages | Purpose |
| :--- | :--- | :--- |
| **Container Engine** *(Required for ISO build)* | `podman` *(recommended)* or `docker` | Containerized pipeline build (`cd build && make iso`). |
| **Virtualization & Emulation** *(Testing)* | `qemu-system-x86`, `edk2-ovmf`, `virt-manager`, `libvirt` | Booting the Live ISO (`build/scripts/test-iso-qemu.sh`) in BIOS or UEFI mode. |
| **Disk & Image Utilities** | `parted`, `mtools`, `dosfstools`, `e2fsprogs`, `xorriso` | Generating synthetic USB test images and extracting `toram` boot images. |
| **Python & QA Suite** | `python3` (>=3.10), `uv` (recommended) or `pip`, `ruff`, `pytest`, `shellcheck` | Running `./scripts/check.sh` and local unit test suites. |

### Developer commands

Run `make` from the repository root to list the available tasks:

```sh
make check       # Full QA suite (same as ./scripts/check.sh)
make test        # Daemon and build unit tests
make lint        # Ruff and ShellCheck
make validate    # TOML syntax and organizer directives schemas
make iso         # Containerized ISO build (requires GALLOS_GRUB_PASSWORD_HASH)
make qemu-test   # Headless smoke test of an existing ISO
```

The root Makefile delegates ISO builds to `build/Makefile` and QEMU runs to the existing boot-test script. These tasks require their respective container or QEMU dependencies; they are not prerequisites for `make help` or unit tests. See the [developer task reference](./docs/DEVELOPMENT.md#root-task-runner) for options, formatting, and cleanup commands.

### Contributing and reporting problems

Use the [bug report](./.github/ISSUE_TEMPLATE/bug_report.yml) or [hardware / firmware compatibility report](./.github/ISSUE_TEMPLATE/hardware_report.yml) form when opening an issue. Include the commit or ISO version, reproduction steps, and evidence; distinguish VM results from physical hardware tests. Blank issues remain available for other topics, including tournament profile requests.

Pull requests use a [short checklist](./.github/PULL_REQUEST_TEMPLATE.md) covering `make check`, Conventional Commits, independently reviewable commits, and documentation consistency. See [the contributor guidelines](./AGENTS.md) for the repository rules.

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

The scenarios below describe intended uses. Restrictions depend on Organizer policy, and venue workflows remain subject to the acceptance gates in [`ROADMAP.md`](./ROADMAP.md#release-acceptance).

```text
+---------------------------------------------------------------------------------------------------+
|  1. Weekly Club Practice & Classes : Neutral open-practice policy; anti-AI website policy pending   |
|                                      CPC-GALLOS identity is an opt-in runtime profile               |
|  2. Multi-Day Training Camps       : Scheduled Event/Contest policy transitions                    |
|                                      Persistent event-data is kept outside Contest by policy        |
|  3. Official Tournaments (ICPC/IOI): Organizer-configured Contest network/device restrictions       |
|                                      Clean session transition; venue acceptance still open          |
+---------------------------------------------------------------------------------------------------+
```

- **Local TOML Configuration:** Store the Organizer policy on the approved boot medium. During a contest, an authorized Organizer can make a last-minute correction in `/etc/gallos/gallos.toml` and run `gallosctl reload`; invalid TOML leaves the active policy in place and reports an error.
- **Baked-In Practice Baseline:** The ISO includes a neutral, open practice profile when no Organizer policy is supplied. Installed tools remain usable without internet.
- **Optional Local Workspace:** Outside `Contest`, the host-mounted `event-data` partition exposes `/media/event-data/contestant` for files the contestant intentionally saves. Contest entry must unmount it before releasing the fresh session. Manual USB export and organizer-allowed external services are separate options (see [`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md) § Mode Hierarchy).

---

## 📚 Architectural & Context Documentation

The repository includes comprehensive context documents and architectural specifications:

- **[`AGENTS.md`](./AGENTS.md):** Guidelines, conventions, and context for AI pair-programming agents and human contributors — the canonical ruleset.
- **[`ROADMAP.md`](./ROADMAP.md):** Seven implementation phases, the selected release core, optional expansion scope, and a separate release-acceptance tracker.
- **[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md):** Current architecture and planned capabilities, including OverlayFS/SquashFS, the Wayland session, and deployment models. Consult the roadmap for implementation status.
- **[`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md):** Canonical `gallos.toml` directives, the 3-tier mode hierarchy ($\text{Contest} \succ \text{Event} \succ \text{Default}$), and planned Organizer configuration tools.
- **[`docs/BUILD_SYSTEM.md`](./docs/BUILD_SYSTEM.md):** The Containerized Build Pipeline (`gallos-builder`), `build.toml` configuration format, and custom ISO generation workflows.
- **[`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md):** Development workflows, Dev Containers / GitHub Codespaces setup, local QA with `./scripts/check.sh`, pre-commit hooks, and CI gate checks.
- **[`docs/WAYLAND_DESKTOP.md`](./docs/WAYLAND_DESKTOP.md):** Wayland desktop specification (Labwc + Waybar + Foot + Mako), current keybindings, implementation status, and planned UI controls.
- **[`docs/BOOT_BRANDING.md`](./docs/BOOT_BRANDING.md):** Design (not yet implemented, targets Phase 4) for a custom Plymouth boot splash and GRUB boot menu theme, plus an inventory of remaining stock-Ubuntu branding to remove.
- **[`docs/ROOT_ACCESS.md`](./docs/ROOT_ACCESS.md):** Local root recovery (`su` during a normal session, or a password-protected tty1 prompt after transition failure). It requires a locally declared password hash.
- **[`docs/HARDWARE_COMPATIBILITY.md`](./docs/HARDWARE_COMPATIBILITY.md):** Firmware support (UEFI SecureBoot & Legacy BIOS), RAM boot (`toram`), and minimal hardware specs.
- **[`docs/ANTI_CHEAT_AND_SECURITY.md`](./docs/ANTI_CHEAT_AND_SECURITY.md):** Threat model and implementation distinctions for policy-scoped network/device controls, application settings, and planned restrictions.
- **[`docs/COMPARATIVE_ANALYSIS.md`](./docs/COMPARATIVE_ANALYSIS.md):** Source-based comparison of reference systems, with GallosOS capabilities presented as target design and checked against the roadmap for implementation status.
- **[`docs/PROVENANCE.md`](./docs/PROVENANCE.md):** Comprehensive ledger tracking all vendored, forked, and adapted third-party code, scripts, and attribution terms.

---

## 🎯 Key Pillars

1. **Ubuntu 24.04 LTS Base & UEFI Secure Boot:**
   - Built on Ubuntu 24.04 LTS "Noble Numbat" (Linux Kernel 6.8+), using Canonical package mirrors during builds. The project has not published official ISO download mirrors or release artifacts yet; GitHub Releases and a secondary mirror remain release-distribution plans.
   - GallosOS and Maratona Linux both use Debian-family packaging, but that alone does not establish binary compatibility or integration with Maratona/ICPC packages; each package requires its own validation.
   - The ISO builder assembles Ubuntu's signed shim, GRUB, and kernel and verifies the latter two against Canonical's certificate. The complete GallosOS Live image reached `multi-user.target` in QEMU with Secure Boot enforced, including a `toram` boot. Physical hardware still requires validation before compatibility can be claimed for a venue.
   - A GRUB BIOS El Torito image and hybrid MBR provide a Legacy BIOS boot path; older lab machines still need venue testing.
   - **Additional base OS versions:** Ubuntu 24.04 is the only accepted base in the current bootstrap script. Alternate releases and matching kernel pairings require implementation and validation (Phase 6).
   - **Optional proprietary GPU drivers:** Driver bundles and persistent MOK workflows remain planned Phase 4 work. The current ISO build does not include the described NVIDIA module.

2. **Containerized ISO Build System:**
   - The ISO generation pipeline runs inside Podman or Docker to avoid installing its build toolchain on the host. Containerization alone does not guarantee bit-for-bit reproducible output across builds or hosts.
   - The current pipeline produces a hybrid `.iso`. Casper has support for mounting `.gsm` layers, but Organizer flashing/injection tools are planned for Phase 5; packaged modules and build-time module copying are planned for Phase 6.
   - VirtualBox/VMware `.ova` and KVM/QEMU `.qcow2` appliance generation is planned for Phase 6. The existing ISO boot workflow does not establish a tested hypervisor compatibility matrix.
   - Windows-based organizers can build and test through WSL2. Direct USB flashing requires `usbipd-win` passthrough and a compatible writer; GallosOS's `gallos-flash` tool is planned for Phase 5. Native Linux remains the primary development target for direct `/dev/sdX` access.

3. **Infrastructure-Agnostic Deployment Model (5-Tier Spectrum):** The architecture describes deployments from **Tier 0** (air-gapped, local policy) through **Tier 1** (network-connected workstations), **Tier 2** (a venue LAN with its Judge Server and shared services), **Tier 3** (an optional GallosOS Venue Controller), and **Tier 4** (integration with institution-managed infrastructure). These tiers describe available venue infrastructure, not GallosOS mode precedence; controller and institutional integrations are not implemented. See [Architecture §10](./docs/ARCHITECTURE.md#10-deployment-infrastructure-spectrum) for definitions and status.
   - The runtime loads policy in order: root-only `/etc/gallos/gallos.toml`, approved boot-medium policy, one unique named profile, then the bundled baseline. A custom ISO may embed a trusted HTTPS source that updates only that bundled baseline. Boot arguments, DHCP options, and arbitrary attached disks do not supply policy. An Organizer can edit the root-only override during Contest and reload through `gallosctl`.
   - Custom ISOs can embed an Organizer's HTTPS policy URL at build time. GallosOS loads the bundled Organizer profile immediately, then polls and applies valid TOML updates while running; machines that boot offline keep that local policy and retry every five minutes. See [Build System](./docs/BUILD_SYSTEM.md) and [Configuration Delivery](./docs/CONFIG_SPEC.md#2-configuration-delivery-methods). DHCP-driven config distribution, fleet monitoring, and the Venue Controller remain future features.

4. **Mode Scheduling and Time:**
   - The daemon evaluates configured absolute Contest/Event windows and supports monotonic `duration_minutes` for automatic-on-boot or manually triggered Contest sessions.
   - The current build does not use `chrony` synchronization state to choose between wall-clock and relative schedules. A visible time-synchronization indicator is not implemented.

5. **Contestant and Organizer Tools:**
   - `gallosd` implements configuration reload and mode transitions. The Config Builder, `gallos-convert`, `gallos-flash`, and `gallos-inject` are planned Phase 5 tools.
   - EarlyOOM desktop notifications and the `gallos-print` CUPS subsystem are planned Phase 4 work.
   - Venue messaging and audit tools are planned Phase 7 capabilities; see [`ROADMAP.md`](./ROADMAP.md) for their scope.

6. **Layered Live Storage:**
   - The current image uses a read-only base SquashFS and a `tmpfs` writable OverlayFS layer. Casper can mount `.gsm` layers, while packaged modules and their build-time assembly remain planned Phase 6 work.
   - Contest scratch cleanup and optional host-mounted `event-data` are separate mechanisms. The `tmpfs` upper layer is lost at reboot; optional persistent storage writes to its own partition outside Contest under the configured policy.
   - The host service manages optional `event-data` outside Contest. USB and persistent-storage behavior depends on the active Organizer policy and remains subject to release acceptance.

7. **Policy-Scoped Security:**
   - The neutral ISO allows open practice and USB storage. Organizer policies can enable restricted network and USB-storage controls using the firewall, local proxy, and device helpers.
   - Browser and application policy must be checked in the installed application. Broad anti-AI website/search restrictions remain planned; central image attestation and judge-side fleet controls require external services and are not implemented here.
   - Enforcement depends on the selected policy and must be verified on the live image. No “zero-leak” or complete USB anti-substitution guarantee is claimed.

8. **Resource Protection:**
   - EarlyOOM is configured with process avoidance/preferences, and `gallosd.service` receives a negative OOM score adjustment. A notification bridge, per-user process/stack limits, CPU-frequency controls, and core pinning are not delivered by the current build.
   - This configuration does not guarantee deterministic performance or immunity from memory pressure.

9. **White-Label Branding (Phase 4 Design):**
   - Extend the existing desktop wallpaper support with configurable Plymouth/GRUB assets, themes, logos, and bookmarks. The complete branding engine is planned; configuration fields do not establish that these asset pipelines are implemented.

10. **Wayland Contestant Desktop:**
    - The base session provisions Labwc, Waybar, Foot, Mako, and an application launcher. Wayland changes the desktop security model but does not eliminate all keylogging or screen-capture risks.
    - Keyboard switching is incomplete: `Super + Space` and `Alt + Shift` invoke a helper that records a layout name and sends a notification, but does not apply a compositor layout. Applying configured layouts and adding a Waybar switcher remain Phase 4 work.

11. **Offline and Personal-Hardware Goals:**
    - The Live image is designed to run without a persistent installation, and the selected core packages are intended to support offline practice. Boot, network devices, graphics, and peripheral support still depend on hardware-specific validation.
    - BYOD deployment guidance and credential-handling tools are not a substitute for release acceptance on the target hardware.

12. **Language and Offline References:**
    - An English-first desktop and bundled offline references are goals, not an enforced contestant-language policy. Offline documentation and dictionaries are planned for Phase 4.
    - Restricted-profile translation and web-relay decisions belong to the deferred anti-AI website/search work.

13. **Optional Venue Services and Auditing:** Venue Controller services, authorized screenshots, keystroke/input forensics, fleet metrics, and audit export are planned for Phase 7. The neutral ISO does not require a Venue Controller; the current source does not provide the described auditing or proctoring pipeline.

14. **Dynamic 3-Tier Mode Hierarchy:**
    - Building upon the foundational design of huronOS, the core scheduling engine dynamically transitions the OS state between three strict modes: **Contest $\succ$ Event $\succ$ Default**.
    - During a `Contest` transition, the daemon invokes session cleanup and applies the configured network/storage policy; it keeps the kiosk stopped if enforcement or cleanup fails. Visible mode controls, countdown display, updated branding, and complete contestant-session behavior remain acceptance or Phase 4 work.

---

## 📖 Terminology

The following terms are used consistently across all GallosOS documentation:

| Term | Definition |
| :--- | :--- |
| **Contestant** | A programmer actively competing or practicing at a GallosOS workstation. The OS user account is always the fixed, unprivileged `contestant` system user. The canonical term throughout GallosOS documentation; avoid *participant* except when quoting an external source verbatim. |
| **Organizer** | The person or committee responsible for configuring and deploying GallosOS for an event. Manages `gallos.toml`, may use the planned `gallos-flash` tool, and may operate an optional Venue Controller. Synonymous with *contest director* or *jury*. |
| **Venue Controller** | An optional dedicated machine that runs on the contest LAN to provide centralized fleet monitoring, DHCP/NTP, CUPS print spooling, MAC-to-team identity mapping, and audit log aggregation. It is part of the Tier 3 deployment option in [Architecture §10](./docs/ARCHITECTURE.md#10-deployment-infrastructure-spectrum); GallosOS also works without one. |
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
│   ├── PULL_REQUEST_TEMPLATE.md # Change summary, validation evidence, and contribution checklist
│   ├── ISSUE_TEMPLATE/        # Bug and hardware / firmware compatibility report forms
│   └── workflows/            # Code quality and ISO boot verification
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
- **[ICPC-Env](https://github.com/icpc-environment/icpc-env)**: The Southeast USA Regional's contestant-environment repository, with examples of toolchain setup, network filtering, and offline documentation. GallosOS uses it as a reference; its systems are not implied to exist in GallosOS.
- **[IOI Contestant-VM](https://github.com/ioi-2025/contestant-vm)**: Official IOI environment standards, minimal desktop configuration, and automated VM provisioning.
