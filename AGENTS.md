# AGENTS.md — GallosOS Developer & Agent Guidelines

Welcome to the **GallosOS** repository. This document serves as the single source of truth for AI agents (and human contributors) working on the architecture, build systems, configuration engines, and documentation of GallosOS.

---

## 🧭 Project Purpose & Vision

**GallosOS** is a modern, lightweight, modular, and reproducible Linux Live distribution engineered specifically for competitive programming contests (ICPC, IOI, Codeforces, university invitationals, and training camps).

It is designed as a **modern drop-in replacement for huronOS** across the Mexican competitive programming ecosystem (**ICPC Gran Premio de México**, **OMI** — *Olimpiada Mexicana de Informática*, **TCMX** — *Training Camp México*, university training camps, and invitationals) while offering a ready-to-use, first-class alternative for international tournaments globally.

It bridges the best ideas from previous projects:

- **HuronOS:** Modular SquashFS layers, Live USB overlay, multi-mode (`Contest > Event > Default`) time-based execution.
- **Maratona Linux:** Proven Latin American contest packages (`maratona-firewall`, BOCA judge integration).
- **ICPC-Env & IOI Contestant-VM:** Standardized language toolchains, offline documentation, and VM automation.
- **Global Parity (NOI Linux 2.0 & Regional ICPC):** Comprehensive compiler parity (GCC 9–14, Free Pascal, Clang, Rust) and air-gapped evaluation guarantees.

While solving their shortcomings:

- Building on **Ubuntu 24.04 LTS** (Canonical global package mirrors + GitHub CDN for releases, widespread driver support).
- Fully containerized builds using **Podman / Docker** (no host pollution; works on Linux, macOS, and Windows WSL2).
- Zero-leak **Anti-Cheat integrity shield** (kernel packet filtering, AI plugin purging, telemetry stripping).
- **White-label branding engine** for universities and event organizers.
- Native **Wayland Kiosk** (Labwc + Waybar) desktop with process-level security isolation.
- Parallel **multi-USB mass flashing tool** (`gallos-flash`).

---

## 📁 Repository Layout

```text
GallosOS/
├── AGENTS.md                  # This file (guidelines for agents & contributors)
├── ROADMAP.md                 # Development phases and feature checklist
├── README.md                  # Project overview and quickstart
├── docs/                      # Architectural & design specifications
│   ├── ARCHITECTURE.md        # Detailed system design, Wayland, OverlayFS, Build & VM testing
│   ├── CONFIG_SPEC.md         # Canonical TOML directives, GallosOS Config Builder, mode hierarchy & .hdf migration
│   ├── BUILD_SYSTEM.md        # Containerized Build Pipeline & build.toml specification
│   ├── WAYLAND_DESKTOP.md     # Wayland kiosk desktop spec, Labwc/Waybar dotfiles, keybinds & UX
│   ├── HARDWARE_COMPATIBILITY.md # Firmware support (UEFI SecureBoot & Legacy BIOS), RAM specs
│   ├── ANTI_CHEAT_AND_SECURITY.md# Firewall, Anti-Cheat protection, telemetry block, USB lock, keyboards
│   ├── COMPARATIVE_ANALYSIS.md# In-depth comparison: GallosOS vs HuronOS vs Maratona vs ICPC vs IOI
│   └── PROVENANCE.md          # Third-party code, vendored assets & attribution ledger
├── examples/                  # Production-ready gallos.toml configuration profiles
│   ├── README.md              # Profile catalog, gallos.toml vs machine.toml, deployment & config precedence
│   ├── icpc-onsite.toml       # ICPC Regional / World Finals (BOCA/DOMjudge, GCC 14, Java 21)
│   ├── maratona-sbc.toml      # Maratona SBC / South America Regional (BOCA, ABNT2, GCC 14)
│   ├── icpc-online-exam.toml  # ICPC Preliminary Online (CodeChef Exam Mode lockdown)
│   ├── codeforces-training.toml # Camp & practice mode (Codeforces, AtCoder, Clang, Rust)
│   ├── ioi-cms.toml           # IOI / National Olympiad (CMS Judge, C++23 focus)
│   └── omegaup-omi.toml       # OMI & Latin American Olympiads (omegaUp platform)
└── schema/                    # Directives validation schemas
    └── directives.schema.json # JSON Schema for gallos.toml (taplo integration)
```

## 🗂️ Organization-Wide Repository Map

GallosOS follows a **hybrid mono/poly-repo strategy**: the core build pipeline, docs, and configs live in this monolith. Standalone organizer-facing tools with independent release cycles live in sibling repos under the `CPC-GALLOS` org.

The core is kept as a single monorepo (rather than splitting build pipeline, daemon, docs, and configs across separate repos the way huronOS and Maratona Linux do) for two reasons: it avoids the maintainer-fragmentation that left both predecessor projects with scattered, inconsistently-updated repos and no single space where a new contributor could see the whole system at once; and it keeps AI-assisted development coherent — one tree with one set of cross-referenced docs lets an agent (or a small contributor base) reason about the full system instead of losing context switching between repos, which matters for a project expected to be maintained by one or a few people rather than a large team.

| Repo | Language | Audience | Status |
| :--- | :--- | :--- | :--- |
| `GallosOS` (this repo) | Bash/Python, TOML | Build pipeline, docs, configs | Active |
| `gallos-flash` | Rust | Organizer (mass USB flashing) | Planned (Phase 5) |
| `gallos-convert` | Rust | Organizer (HuronOS `.hdf` migration) | Planned (Phase 5) |
| `gallos-config-builder` | Angular/TS | Organizer (visual TOML editor) | Planned (Phase 5) |

Vendored/forked third-party code (Casper hooks, `ipman`, etc.) lives inside this monolith under `vendor/inherited/`, not as separate repos — see [`docs/PROVENANCE.md`](./docs/PROVENANCE.md) for the full ledger.

---

## 🛠️ Operating Principles for AI Agents

When assisting in this repository, follow these core tenets:

1. **English as the Sole Repository Language:**
   All documentation, architectural design documents, code comments, schema descriptions, diagrams, and commit messages MUST be written strictly in clear, professional English.

2. **Accurate Project Status & Non-Misleading Claims:**
   GallosOS is currently in the **architectural design and specification phase**. Never state or imply that GallosOS has undergone empirical hardware benchmarking, physical write speed tests, or real-world laboratory trials. Frame all comparative analyses strictly as **conceptual and architectural evaluations** derived from binary inspection and source analysis of the reference distributions and production contest images.

3. **Factual Grounding, Real Links & Zero Hallucination Policy:**
   - **Zero Hallucination:** Every technical claim, package name, version number, compiler flag, kernel parameter, and architectural feature MUST be grounded in reality and cross-referenced with local reference trees (`HuronOS/`, `maratona-linux/`, `icpc-env/`, `contestant-vm/`) or official upstream sources.
   - **Verifiable & Canonical Links:** All references, headers, and citations in documentation and example files (`examples/*.toml`) MUST point to real, publicly accessible URLs (official contest PDFs, official GitHub repositories, or authoritative contest committee portals). Never fabricate links, use placeholder domains, or cite non-existent publications.
   - **Unambiguous Specificity:** Avoid vague claims or hand-waving. Specify exact package versions (e.g. GCC 14.2.0, OpenJDK 21.0.8, Free Pascal 3.0.4) and verify package lifecycles before claiming software is deprecated or active.

4. **Cross-Document Coherence & Integrity:**
   All architectural decisions, naming conventions (e.g. `gallos.toml`, `GallosOS Config Builder`, `directives.schema.json`), directory layouts, and mode precedence rules MUST remain 100% coherent and synchronized across `README.md`, `ROADMAP.md`, `docs/`, `examples/`, and schemas. Never introduce conflicting terminology or contradictory specifications between documents.

5. **Maintain Mode Hierarchy:**
   Preserve the strict 3-tier precedence:
   $$\text{Contest} \succ \text{Event} \succ \text{Default (Always)}$$
   - `Contest`: Strict lockdown, active time-window, judge-only network, fresh isolation, optional auditing & proctoring.
   - `Event`: Training camp / warm-up, persistent workspace between classes, hides previous data in contest.
   - `Default`: General fallback mode when no scheduled window is active.

6. **Anti-Cheat by Default:**
   Ensure all proposed scripts, configs, and IDE setups strictly disable and block:
   - GitHub Copilot, JetBrains AI Assistant, Cursor, Supermaven, Cody, Claude/OpenAI endpoints (via DNS blocklists like `ai.robots.txt`).
   - Telemetry reporting in VSCodium, Chromium, and Firefox.

7. **Containerized Reproducibility:**
   Never assume host-installed packages. Prefer Podman/Docker recipes or self-contained scripts capable of running inside containers or WSL2 with `usbipd-win`.

8. **Clarity & Brevity in Code & Configs:**
   Use explicit typing and clear documentation. When generating configuration files, use **TOML (`gallos.toml`)** as the sole canonical format (using `gallos-convert` for legacy HuronOS `.hdf` migration), validated by `schema/directives.schema.json`.

9. **Canonical Terminology & Infrastructure-Agnosticism:**
   Always use the following terms as defined in `README.md § Terminology`:
   - **Contestant** — the programmer at the workstation (`contestant` Linux user). Preferred over *participant*.
   - **Organizer** — the person/committee configuring and deploying GallosOS.
   - **Venue Controller** — the optional dedicated local server (Tier 3). Never conflate with the Judge Server.
   - **Judge Server** — the external judge system (BOCA, DOMjudge, CMS, omegaUp). GallosOS never hosts it.

   GallosOS is **infrastructure-agnostic**: it operates across a 5-tier spectrum from fully air-gapped (Tier 0) to externally managed institutional infrastructure (Tier 4). Never assume the presence of a Venue Controller, internet connectivity, or any specific network service when designing features or writing documentation.

10. **In-Band vs Out-of-Band Tooling Philosophy:**
    Adhere strictly to the tooling separation defined in the architecture:
    - **In-Band (Live OS Core):** Any script running *inside* the contest environment (`gallos-daemon`, hooks) MUST be written in **Bash or Python** to guarantee on-the-fly hackability during a regional event without needing a compiler.
    - **Out-of-Band (Organizer CLI Tools):** Any tool run by the organizer on their host machine (`gallos-flash`, `gallos-convert`) MUST be built as **Statically Compiled Binaries (Rust)** to prevent dependency hell and ensure they work instantly.

---

## 💻 Cross-Platform & Virtualization Support

Agents should ensure instructions and tooling support:

- **Native Linux:** Ubuntu, Fedora, Debian, Arch.
- **Windows Subsystem for Linux (WSL2):** With `usbipd-win` for direct USB drive passthrough and flashing.
- **Testing Environments:**
  - **QEMU / KVM (Virt-Manager)** for rapid headless or graphical testing.
  - **VirtualBox & VMware Workstation** for validating guest additions and UEFI live booting.

---

## 🤝 Contribution Protocol

- Format all Markdown files using GitHub-flavored Markdown in English.
- Use Mermaid diagrams for complex multi-tier architectures.
- Include practical code snippets, TOML blocks, and shell commands.
- Keep documentation up-to-date whenever system specifications evolve.
