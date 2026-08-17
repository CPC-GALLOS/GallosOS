# GallosOS

> [!WARNING]
> **Work In Progress - Architectural Phase:** GallosOS is currently in the active design and specification phase. The repository serves as an RFC (Request for Comments) and architectural blueprint. Code implementations, hardware benchmarking, ISO generation tools, and formal academic publications are not yet available.

**GallosOS** is a modern, lightweight, modular, and reproducible Linux Live distribution engineered specifically for competitive programming across **all scenarios**: weekly university club practices, multi-day training camps, and official ICPC / IOI style tournaments.

GallosOS is designed as a **seamless, modern drop-in replacement for [huronOS](https://huronos.org)** across the Mexican competitive programming ecosystem (**ICPC Gran Premio de México**, **OMI** — *Olimpiada Mexicana de Informática*, and university invitationals), while scaling as a world-class, globally adaptable solution for international contests (ICPC World Finals/Regionals, IOI, and Maratona SBC).

It synthesizes the foundational architectural strengths of **huronOS** (multi-mode scheduling & layered storage), **[Maratona Linux](https://maratona.ime.usp.br/)** (Latin American BOCA judge integration), **[ICPC-Env](https://github.com/icpc-environment/icpc-env)** (standardized toolchains), and the **[IOI-2025 Contestant-VM](https://github.com/ioi-2025/contestant-vm)** (CMS auditing & proctoring), providing a lightweight, tamper-resistant, and white-label operating system evaluated against the entire global competitive programming landscape (including China's **NOI Linux 2.0** and European/Asian ICPC systems).

---

## 🎯 Designed for All Competitive Programming Contexts

```text
+---------------------------------------------------------------------------------------------------+
|  1. Weekly Club Practice & Classes : Immutable USB + cloud sync (GitHub/GitLab/GDrive)            |
|                                      Controlled browsing: no AI results, curated bookmarks        |
|  2. Multi-Day Training Camps       : Automated transitions (Event -> Contest -> Upsolving)        |
|                                      Cloud sync suspended during Contest windows                   |
|  3. Official Tournaments (ICPC/IOI): Strict Anti-AI lockdown, judge-only network, fresh isolation |
|                                      Code packaged as .tar.gz at contest end for USB export       |
+---------------------------------------------------------------------------------------------------+
```

- **Dynamic Online Configuration:** Host a single canonical `gallos.toml` directives file (or legacy `.hdf` migrated via `gallos-convert`) on a **GitHub Gist**, Raw repository, or campus server and update contest times, allowed websites, or bookmarks on the fly *without re-flashing USB drives*.
- **Baked-In Offline Fallback:** Embed configurations directly onto the USB image at burn-time for 100% offline, air-gapped laboratory environments.

---

## 📚 Architectural & Context Documentation

The repository includes comprehensive context documents and architectural specifications:

- **[`AGENTS.md`](./AGENTS.md):** Guidelines, conventions, and context for AI pair-programming agents and human contributors.
- **[`ROADMAP.md`](./ROADMAP.md):** The step-by-step engineering checklist and feature tracker broken down into Alpha, Beta, and RC phases.
- **[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md):** Layered filesystem (OverlayFS + SquashFS), Wayland kiosk desktop (Labwc + Waybar), containerized build engine (Podman/Docker), Windows WSL2 + `usbipd-win` workflows, and VM deployment matrices (`.ova`, `.qcow2`).
- **[`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md):** Canonical `gallos.toml` directives specification, GallosOS Config Builder web/GUI configurator, 3-tier mode hierarchy ($\text{Contest} \succ \text{Event} \succ \text{Default}$), and `gallos-convert` migration tool.
- **[`docs/HARDWARE_COMPATIBILITY.md`](./docs/HARDWARE_COMPATIBILITY.md):** Firmware support (UEFI SecureBoot & Legacy BIOS), RAM boot (`toram`), and minimal hardware specs.
- **[`docs/ANTI_AI_AND_SECURITY.md`](./docs/ANTI_AI_AND_SECURITY.md):** Threat model, `nftables` kernel packet filtering, AI extension purging (VSCodium / JetBrains), telemetry disabling, USB storage locking, and keyboard layout switching.
- **[`docs/COMPARATIVE_ANALYSIS.md`](./docs/COMPARATIVE_ANALYSIS.md):** Detailed, source-verified comparison matrix evaluating GallosOS against HuronOS, Maratona Linux, ICPC-Env, and IOI Contestant-VM.

---

## 🎯 Key Pillars

1. **Ubuntu 24.04 LTS Base & GitHub Releases CDN:**
   - Avoids single-point-of-failure download bottlenecks by utilizing Canonical's global package mirrors for base packages and GitHub's global CDN for GallosOS releases and tools.
   - Architected to leverage Ubuntu's extensive out-of-the-box hardware driver support for modern Intel/AMD processors, Wi-Fi 6E/7, and Ethernet chipsets.

2. **Containerized & Reproducible Build System:**
   - The proposed isolated OCI build container (Podman / Docker) aims to guarantee identical ISO generation on Linux, macOS, and Windows WSL2 without polluting the host OS.
   - Continuous Integration QA via GitHub Actions.

3. **End-to-End Contestant & Organizer Tooling Suite:**
   - **GallosOS Config Builder:** Web & GUI app to visually construct and validate `gallos.toml` directives without manual text editing.
   - **`gallos-convert`:** One-command CLI migration from legacy HuronOS `.hdf` files to canonical TOML.
   - **`gallos-flash`:** Parallel multi-USB mass flashing tool with native WSL2 + `usbipd-win` support.
   - **`gallos-daemon` & `gallos-oom-notify`:** Real-time mode switching, EarlyOOM memory guard, and visual desktop notifications.

4. **Multi-Layered Immutable Storage (OverlayFS):**
   - Read-only base SquashFS + modular software packages (`.gsm`).
   - Ephemeral RAM `tmpfs` upper layer ensures a pristine clean state upon reboot.
   - Automatic contestant source code archiving (`contest-YYYYMMDDTHH-MM-SS.tar.gz`) exported securely over the network to the Venue Controller (or manually via secondary external USB).

5. **Zero-Leak Anti-AI Shield:**
   - Kernel-level packet filter (`nftables`) with a default-DROP policy, whitelisting only designated judges (BOCA, DOMjudge, Codeforces) and local DNS/NTP.
   - Telemetry-stripped **VSCodium** and **JetBrains Community Editions** (IntelliJ IDEA CE, PyCharm CE) with all AI assistant plugins strictly removed. (Support for sponsored JetBrains Pro offline license injection is treated as an optional future extension for sponsored championship finals).

6. **White-Label University Branding:**
   - Declarative `branding/` folder (`branding.toml`, wallpapers, Plymouth boot splash, and browser bookmarks) allowing institutions to brand contest ISOs in seconds.

7. **Process-Isolated Wayland Desktop:**
    - Wayland compositor (Labwc) paired with Waybar (featuring an integrated dropdown menu launcher), eliminating X11 keylogging and screen-snooping vulnerabilities.
    - Hotkey and status bar-driven keyboard layout switching (`latam`, `us`, `es`, `br-abnt2`, `dvorak`).

8. **Ephemeral & Non-Destructive (BYOD-Friendly):**
    - Booting from a Live USB solves infrastructure compatibility problems by leaving the host computer's hard drive untouched. This makes it safe and viable for both highly controlled university labs and low-resource environments.
    - **Contextualized for Latin American Realities:** We acknowledge the disparity in computational and network infrastructure across the region. Having an offline-capable system that runs entirely from RAM ensures that events can happen successfully even in environments with scarce or practically non-existent connectivity.
    - Ideal for university programming clubs: students can bring their own personal laptops (BYOD, which typically run Windows). The official recommendation is to boot GallosOS during club sessions so students get accustomed to the exact same distraction-free, standardized environment used in official contests, building familiarity without permanently altering their personal OS.

---

## 📖 Terminology

The following terms are used consistently across all GallosOS documentation:

| Term | Definition |
| :--- | :--- |
| **Contestant** | A programmer actively competing or practicing at a GallosOS workstation. The OS user account is always the fixed, unprivileged `contestant` system user. Preferred term throughout GallosOS documentation; *participant* may appear occasionally and is considered equivalent. |
| **Organizer** | The person or committee responsible for configuring and deploying GallosOS for an event. Manages `gallos.toml`, runs `gallos-flash`, and optionally operates the Venue Controller. Synonymous with *event director* or *scientific committee member*. |
| **Venue Controller** | An optional dedicated machine (or GallosOS USB in Server Mode) that runs on the contest LAN to provide centralized fleet monitoring, DHCP/NTP, CUPS print spooling, MAC-to-team identity mapping, and audit log aggregation. Only required for Tier 3 deployments — GallosOS works without one. |
| **Judge Server** | The external competitive programming judge system (BOCA, DOMjudge, PC², CMS, omegaUp) running on a separate dedicated machine managed by the contest organizer. GallosOS **never** hosts the judge — it connects to it. |

---

## 📁 Repository Layout

```text
GallosOS/
├── AGENTS.md                  # Project rules for AI agents and human contributors
├── ROADMAP.md                 # Development phases and feature checklist
├── README.md                  # Project overview and quickstart
├── LICENSE                    # GNU General Public License v2.0 or later
├── docs/                      # Architectural & design specifications
│   ├── ARCHITECTURE.md        # System design, Wayland, OverlayFS, Build & VM testing
│   ├── CONFIG_SPEC.md         # Canonical TOML directives, GallosOS Config Builder & mode hierarchy
│   ├── HARDWARE_COMPATIBILITY.md # Firmware support (UEFI SecureBoot & Legacy BIOS), RAM specs
│   ├── ANTI_AI_AND_SECURITY.md# Firewall, Anti-AI protection, telemetry & USB lockdown
│   └── COMPARATIVE_ANALYSIS.md# In-depth comparison with existing contest distributions
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
- **[ICPC-Env](https://github.com/icpc-environment/icpc-env)**: Squid domain filtering, WireGuard fleet management, and offline DevDocs setups.
- **[IOI Contestant-VM](https://github.com/ioi-2025/contestant-vm)**: Official IOI environment standards, minimal desktop configuration, and automated VM provisioning.
