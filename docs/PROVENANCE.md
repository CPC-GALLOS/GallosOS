# GallosOS Provenance & Third-Party Code Ledger

This document serves as the canonical registry tracking all third-party software, scripts, configuration patterns, and toolchains vendored, forked, adapted, or evaluated within the **GallosOS** project.

This ledger ensures that all intellectual property, upstream inspirations, and imported dependencies are explicitly documented, audited for license compatibility, and attributed to their original authors.

---

## 🏛️ Code Provenance & Vendoring Architecture

GallosOS operates on a **hybrid mono/poly-repo strategy**:

```text
CPC-GALLOS Organization
├── GallosOS (Monorepo)
│   ├── build/                 # Containerized Live ISO build pipeline
│   ├── daemon/                # In-band gallos-daemon (Python core service)
│   ├── docs/                  # System architecture specifications & this ledger
│   ├── examples/              # Canonical gallos.toml configuration profiles
│   ├── schema/                # Taplo directives validation schemas
│   └── vendor/inherited/      # Vendored third-party code & inherited scripts
│       ├── maratona-casper/   # (Planned) Inherited Casper hooks
│       └── huronos-ipman/     # (Planned) Inherited network helper scripts
└── Sibling Repositories (Poly-Repo Organizer Tooling)
    ├── gallos-flash           # Standalone mass USB flashing tool (Rust)
    ├── gallos-convert         # Standalone HuronOS .hdf migration CLI (Rust)
    └── gallos-config-builder  # Standalone visual web configurator (Angular/TS)
```

### Vendoring & Clean-Room Rules

1. **In-Tree Vendoring (`vendor/inherited/`):** When third-party code (such as Casper initramfs hooks or network helper scripts) is copied or adapted directly into the Live OS build tree, it MUST be placed inside `vendor/inherited/<component-name>/` with its upstream `LICENSE` file and original copyright headers preserved intact.
2. **Clean-Room vs. Direct Vendoring:** Direct vendoring into `vendor/inherited/` is supported for all verified open-source and copyleft-compatible licenses (e.g. MIT, GPL-2.0). When clean-room implementation is chosen instead (e.g. rewriting in Python for `gallos-daemon` alignment or using modern `nftables` syntax over legacy `iptables`), it is done for architectural uniformity and maintainability.
3. **Current Project Status Note:** As GallosOS is currently in the **architectural design and specification phase**, **no third-party code has been physically vendored or forked yet**. All entries below currently reflect evaluated references, clean-room targets, or superseded patterns.

---

## 🚦 Status Legend

| Status | Symbol | Meaning |
| :--- | :---: | :--- |
| **Evaluated** | 🟡 | Research, architectural inspection, or pattern reference only. No upstream code has been vendored into the tree. |
| **Vendored** | 🟢 | Third-party source code has been copied or adapted into `vendor/inherited/` with license and attribution preserved. |
| **Superseded** | ✅ | Evaluated during architectural design, but replaced with a modern or native alternative (rationale documented). |
| **Contacted** | ⚪ | Formal outreach or upstream communication initiated with the authors/maintainers regarding licensing or collaboration. |

---

## 📋 Comprehensive Provenance Ledger

| Component / Subsystem | Upstream Source Repository | Upstream License | Referenced In | Target / Vendored Path | Status | Adaptation Strategy & Notes |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **Casper Live Boot Hooks** | [`maratona-linux/maratona-casper`](https://github.com/maratona-linux/maratona-casper) (Org Fork: [`CPC-GALLOS/maratona-casper`](https://github.com/CPC-GALLOS/maratona-casper)) | `GPL-2.0` | [`ROADMAP.md` Phase 1](../ROADMAP.md#phase-1-bootstrapping-casper--core-filesystem-engine-alpha), [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | `vendor/inherited/maratona-casper/` | 🟡 Evaluated | Inspect boot parameter parsing and union mounting hooks (`OverlayFS`). Adapt for Ubuntu 24.04 `casper` initramfs. |
| **Static IP & Interface Scripts (`ipman`)** | [`huronOS/huronOS-build-tools`](https://github.com/huronOS/huronOS-build-tools) (Org Fork: [`CPC-GALLOS/huronOS-build-tools`](https://github.com/CPC-GALLOS/huronOS-build-tools)) | `GPL-2.0` | [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | `vendor/inherited/huronos-ipman/` | 🟡 Evaluated | Network interface discovery and static IP assignment helper. Evaluated for inclusion in `vendor/inherited/`. |
| **EarlyOOM Notification Pattern** | [`huronOS/huronOS-build-tools`](https://github.com/huronOS/huronOS-build-tools) | `GPL-2.0` | [`ROADMAP.md` Phase 2](../ROADMAP.md#phase-2-security-lockdown-anti-cheat-shield--resource-hardening-beta-1), [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | N/A (Superseded) | ✅ Superseded | Evaluated HuronOS's custom OOM notify script. Replaced by native upstream `earlyoom -n` (D-Bus broadcast) paired with standard `systembus-notify` user service. |
| **`.hdf` Configuration Parser & Schema** | [`huronOS/huronOS-build-tools`](https://github.com/huronOS/huronOS-build-tools) (Org Fork: [`CPC-GALLOS/huronOS-build-tools`](https://github.com/CPC-GALLOS/huronOS-build-tools)) | `GPL-2.0` | [`docs/CONFIG_SPEC.md`](./CONFIG_SPEC.md), [`ROADMAP.md` Phase 5](../ROADMAP.md#phase-5-organizer-tooling-suite-rc-1) | Sibling repo `gallos-convert` | 🟡 Evaluated | Reference schema for building the standalone Rust-based `.hdf` $\to$ `gallos.toml` converter CLI (`gallos-convert`). |
| **Contest Firewall Rules & Whitelisting** | [`maratona-linux/maratona-firewall`](https://github.com/maratona-linux/maratona-firewall) | `GPL-2.0` | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md), [`ROADMAP.md` Phase 2](../ROADMAP.md#phase-2-security-lockdown-anti-cheat-shield--resource-hardening-beta-1) | N/A (Clean-room) | 🟡 Evaluated | Conceptual reference for default-DROP policies. Modernized from legacy `iptables` into native Linux `nftables` rulesets managed dynamically by `gallos-daemon`. |
| **Contestant Printing Pipeline (`printfile`)** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) (ICPC World Finals SysOps & SWERC Lyon) | `MIT` (confirmed) | [`ROADMAP.md` Phase 4](../ROADMAP.md#phase-4-specialized-contest-subsystems--branding-beta-3), [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | `vendor/inherited/icpcsysops-printfile/` (or clean-room) | 🟡 Evaluated | Terminal printing pipeline pattern (`a2ps` / `enscript`). MIT license permits direct vendoring into `vendor/inherited/` (with attribution) or clean-room implementation in Python (`gallos-print`). Note: pending path verification in subdirectories. |
| **Keystroke & Input Forensics (`martkeys`)** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) (ICPC World Finals SysOps) | `MIT` (confirmed) | [`ROADMAP.md` Phase 7](../ROADMAP.md#phase-7-venue-controller--advanced-telemetry-post-ga--v20), [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) | `vendor/inherited/icpcsysops-martkeys/` | 🟡 Evaluated | Kernel-level `/dev/input/event*` activity aggregator architecture (`parse_martkeys` at repo root). MIT license permits direct vendoring with copyright notice preserved; clean-room Python rewrite remains an option for native daemon consistency. |
| **Process Hierarchy & Window Monitor (`s.py`)** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) (ICPC World Finals SysOps) | `MIT` (confirmed) | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md), [`docs/COMPARATIVE_ANALYSIS.md`](./COMPARATIVE_ANALYSIS.md) | `vendor/inherited/icpcsysops-spy/` (or clean-room) | 🟡 Evaluated | Active focused window and process hierarchy forensic sampler. MIT license permits direct vendoring with attribution, though native clean-room Python audit module in `gallos-daemon` is preferred. Note: pending path verification in subdirectories. |
| **Contestant Workspace Backup Mechanism** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible), [`ioi-2025/contestant-vm`](https://github.com/ioi-2025/contestant-vm) | `icpcsysops`: `MIT` (confirmed), `contestant-vm`: `GPL-2.0` | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) | N/A (Clean-room or Vendored) | 🟡 Evaluated | Architectural pattern for automated periodic tar/rsync workspace backups (`roles/icpc_host_backup/files/backup_watchdog`). MIT license allows direct vendoring into `vendor/inherited/` or Python re-implementation in `gallos-daemon`. |
| **Contest Toolchain & Package Manifests** | [`icpc-environment/icpc-env`](https://github.com/icpc-environment/icpc-env), [`maratona-linux/maratona-team-tools`](https://github.com/maratona-linux/maratona-team-tools), [`ioi-2025/contestant-vm`](https://github.com/ioi-2025/contestant-vm) | `icpc-env`: `MIT`, `maratona`: `GPL-2.0`, `contestant-vm`: `GPL-2.0` | [`ROADMAP.md` Phase 6](../ROADMAP.md#phase-6-software-toolchains-virtual-appliances--cicd-ga-release), [`docs/COMPARATIVE_ANALYSIS.md`](./docs/COMPARATIVE_ANALYSIS.md) | N/A | 🟡 Evaluated | Package lists, compiler flags, and editor plugins cross-referenced to ensure 1:1 parity with international contest standards. |

---

## ⚖️ Upstream Licensing Audits & Precautions

### `icpcsysops/ansible` — Confirmed MIT License

The [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) repository contains production playbooks and operational scripts used by the ICPC Systems Operations committee during World Finals and North America Championship (NAC) events.

- **Verified License Status:** The repository includes an explicit `LICENSE` file under the **MIT License**, confirmed via upstream repository inspection and GitHub license detection.
- **GallosOS Compliance & Vendoring Action:**
  1. **Direct Vendoring Permitted:** Direct copying or adaptation into `vendor/inherited/` (e.g. `vendor/inherited/icpcsysops-martkeys/`) is fully permitted under the MIT License, provided that the upstream copyright notice and MIT license text are preserved in each vendored package.
  2. **Clean-Room Remains an Engineering Option:** Clean-room reimplementation in Python (matching `gallos-daemon`'s in-band language requirement) remains an option for architectural elegance and unified logging, but is no longer legally mandated by copyright restrictions.
  3. **Directory Path Verifications:** While `parse_martkeys` is verified at the repository root, other specific scripts (such as `printfile` or `s.py`) will undergo exact path verification in `roles/`, `files/`, or `library/` subdirectories during their respective implementation phases prior to final vendoring.

### GPL-2.0 Copyleft Compatibility

GallosOS is distributed under the **GNU General Public License v2.0 or later (GPL-2.0-or-later)**.

- Code imported from `huronOS` (`GPL-2.0`) and `maratona-linux` (`GPL-2.0`) is fully license-compatible with GallosOS.
- All vendored files in `vendor/inherited/` must retain their original license headers, copyright notices, and author attributions.

---

## 🔄 Protocol for Updating This Ledger

Whenever an AI agent or human contributor proposes importing, vendoring, or adapting external code:

1. **Verify License:** Check the upstream repository for an explicit open-source license (`LICENSE`, `COPYING`, or SPDX identifiers).
2. **Determine Target Location:**
   - Standalone utilities $\to$ Sibling repositories under `CPC-GALLOS`.
   - In-band inherited scripts $\to$ `vendor/inherited/<component>/` in this monorepo.
   - Conceptual patterns $\to$ Clean-room implementation in `daemon/` or `build/`.
3. **Update Status in this Ledger:** Transition the component status from `🟡 Evaluated` to `🟢 Vendored`, `✅ Superseded`, or `⚪ Contacted`, updating the *Target / Vendored Path* and *Notes*.
