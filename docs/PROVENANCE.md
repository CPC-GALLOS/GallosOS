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

Upstream sources (`huronOS-build-tools`, `maratona-casper`, and the other trees below) are kept only as local, gitignored reference clones of the original upstream repositories — not as forks under the `CPC-GALLOS` org. Both upstreams have been inactive for 2+ years, so drift risk between the reference clone and current upstream `HEAD` is low. No standalone fork is maintained; all inherited logic is either vendored in-tree with attribution or clean-room rewritten, per the rules below.

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
| **Casper Live Boot Hooks** | [`maratona-linux/maratona-casper`](https://github.com/maratona-linux/maratona-casper) | `GPL-2.0` | [`ROADMAP.md` Phase 1](../ROADMAP.md#phase-1-bootstrapping-casper--core-filesystem-engine-alpha), [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | `vendor/inherited/maratona-casper/` | 🟡 Evaluated | Confirmed present in the local reference checkout: initramfs hook `55maratona-fixes` (casper-functions integration, clean-home marker, `factoryreset`/`mlinstall` boot-param handling) plus `ml-install.sh`/`ml-factoryreset.sh`. Inspect boot parameter parsing and union mounting hooks (`OverlayFS`). Adapt for Ubuntu 24.04 `casper` initramfs. |
| **Static IP & Interface Scripts (`ipman`)** | [`equetzal/huronOS-build-tools`](https://github.com/equetzal/huronOS-build-tools) | `GPL-2.0` | [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | `vendor/inherited/huronos-ipman/` | 🟡 Evaluated | Confirmed at `base-system/usrroot/usr/sbin/ipman` + `base-system/usrroot/usr/lib/systemd/system/ipman.service`. Reads `sync-server.conf` for a static IP/mask/gateway and falls back to DHCP on the remaining interfaces if none match. Evaluated for inclusion in `vendor/inherited/`. |
| **EarlyOOM Configuration Pattern** | [`equetzal/huronOS-build-tools`](https://github.com/equetzal/huronOS-build-tools) | `GPL-2.0` | [`ROADMAP.md` Phase 2](../ROADMAP.md#phase-2-security-lockdown-anti-cheat-shield--resource-hardening-beta-1), [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | N/A (Pattern confirmed, not vendored) | 🟡 Evaluated | Correction: the local checkout's `base-system/usrroot/etc/default/earlyoom` already invokes upstream `earlyoom` with `EARLYOOM_ARGS="-r 15 -m 10,5 -n"` — the `-n` (D-Bus notify) flag is native huronOS behavior, not a custom script GallosOS is superseding. GallosOS's `earlyoom -n` + `systembus-notify` design directly matches this upstream pattern rather than replacing a distinct one; no separate custom notifier was found in this tree. |
| **`.hdf` Configuration Parser & Schema** | [`equetzal/huronOS-build-tools`](https://github.com/equetzal/huronOS-build-tools) | `GPL-2.0` | [`docs/CONFIG_SPEC.md`](./CONFIG_SPEC.md), [`ROADMAP.md` Phase 5](../ROADMAP.md#phase-5-organizer-tooling-suite-rc-1) | Sibling repo `gallos-convert` | 🟡 Evaluated | Confirmed real tools, not a single monolithic "parser": `base-system/usrroot/usr/sbin/dvar` (directive-variable getter, e.g. `dvar --variable-name Wallpaper --section Always`), `base-system/usrroot/usr/sbin/hos-resolve` (resolves directive domain names to IPs), and `base-system/tools/hsync-validator/hsync-validator.cpp` (schema validator). Reference these three for the standalone Rust-based `.hdf` $\to$ `gallos.toml` converter CLI (`gallos-convert`). |
| **Contest Firewall Rules & Whitelisting** | [`maratona-linux/maratona-firewall`](https://github.com/maratona-linux/maratona-firewall) | `GPL-2.0` | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md), [`ROADMAP.md` Phase 2](../ROADMAP.md#phase-2-security-lockdown-anti-cheat-shield--resource-hardening-beta-1) | N/A (Clean-room) | 🟡 Evaluated | Conceptual reference for default-DROP policies. Modernized from legacy `iptables` into native Linux `nftables` rulesets managed dynamically by `gallos-daemon`. |
| **Static Judge-Host Pinning (`config-ip-boca.sh` pattern)** | [`maratona-linux/maratona-firewall`](https://github.com/maratona-linux/maratona-firewall) | `GPL-2.0` | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) §3.4 | N/A (Clean-room) | 🟡 Evaluated | **Adopted.** Real production script resolves the judge domain once at configure-time and hardcodes the IP directly into `/etc/hosts` (never re-resolved live), sidestepping DNS entirely for self-hosted LAN judges — simpler than a periodic-repin daemon for the non-CDN case. GallosOS adopts this as the primary mechanism for self-hosted judges (BOCA/DOMjudge/CMS); periodic DNS re-resolution is reserved for CDN-fronted judges only. |
| **USB Storage Lockdown via polkit/udisks2** | [`maratona-linux/maratona-usuario-icpc`](https://github.com/maratona-linux) | `GPL-2.0` | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) §5 | N/A (Clean-room) | 🟡 Evaluated | **Adopted.** Real `.pkla` polkit rules deny the contestant user `NetworkManager.*`, `timedate1.*`, and `udisks2.*` actions outright (`ResultAny=no`), blocking USB mass storage via policy denial rather than kernel-module unbinding. GallosOS adopts this as the primary USB-block mechanism; `udev` unbinding is kept as a documented fallback for systems without polkit/udisks2 enforcement. Also documents a real precedent for the "Clean State Wipe" mechanism: `clean-home-now`, a FIFO-triggered (`/dev/shm/icpc-clean-homed.fifo`) home-directory reset daemon. |
| **IPv6 Disablement** | [`equetzal/huronOS-build-tools`](https://github.com/equetzal/huronOS-build-tools) (docs site, `docs/start/requirements.md`) | `GPL-2.0` (docs) | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) §3.1 | N/A (Clean-room) | 🟡 Evaluated | **Adopted.** huronOS's own documentation recommends disabling IPv6 network-wide because its firewall is IPv4-only and dual-stack operation can let contestants reach IPv6-only destinations unfiltered. GallosOS adopts the same posture: `nftables` uses `table ip` (IPv4-only) instead of `table inet`, and IPv6 is disabled at the kernel level. |
| **Contestant Printing Pipeline (`printfile`)** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) (ICPC World Finals SysOps & SWERC Lyon) | `MIT` (confirmed) | [`ROADMAP.md` Phase 4](../ROADMAP.md#phase-4-specialized-contest-subsystems--branding-beta-3), [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | `vendor/inherited/icpcsysops-printfile/` (or clean-room) | 🟡 Evaluated | Path verified: `files/printfile` (repo root `files/`, not nested under `roles/`). Terminal printing pipeline pattern (`a2ps` / `enscript`). MIT license permits direct vendoring into `vendor/inherited/` (with attribution) or clean-room implementation in Python (`gallos-print`). |
| **Keystroke & Input Forensics (`martkeys`)** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) (ICPC World Finals SysOps) | `MIT` (confirmed) | [`ROADMAP.md` Phase 7](../ROADMAP.md#phase-7-venue-controller--advanced-telemetry-post-ga--v20), [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) | `vendor/inherited/icpcsysops-martkeys/` | 🟡 Evaluated | Path verified: the `parse_martkeys` jq pipeline is at repo root as previously cited, but the collector binary itself is `roles/martkeys/files/martkeys` (statically-linked Go binary) with config `roles/martkeys/files/keys.yaml` and a systemd unit. MIT license permits direct vendoring with copyright notice preserved. **See inline comment in `docs/ANTI_CHEAT_AND_SECURITY.md` §8.3** for a real-world default-config nuance flagged for later consideration. |
| **Process Hierarchy & Window Monitor (`s.py`)** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) (ICPC World Finals SysOps) | `MIT` (confirmed) | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md), [`docs/COMPARATIVE_ANALYSIS.md`](./COMPARATIVE_ANALYSIS.md) | `vendor/inherited/icpcsysops-spy/` (or clean-room) | 🟡 Evaluated | Path verified: `roles/team/files/s.py` (not repo root). The process-hierarchy walk (`/proc/<pid>/task/<pid>/children`) is portable; the focused-window half uses X11-only `xprop`/`_NET_ACTIVE_WINDOW` and cannot be ported as-is under Wayland/labwc. **See inline comment in `docs/ANTI_CHEAT_AND_SECURITY.md` §8.4** for a flagged follow-up (needs a `wlr-foreign-toplevel-management`-based replacement). |
| **Contestant Workspace Backup Mechanism** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible), [`ioi-2025/contestant-vm`](https://github.com/ioi-2025/contestant-vm) | `icpcsysops`: `MIT` (confirmed), `contestant-vm`: `GPL-2.0` | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) | N/A (Clean-room or Vendored) | 🟡 Evaluated | Confirmed exactly as cited: `roles/icpc_host_backup/files/backup_watchdog` + `sh.backupclient`. Also confirmed `contestant-vm`'s `bin/ioibackup.sh`: rsync-over-SSH to a remote server with a **100KB per-file cap** and a **1MB/s bandwidth throttle**, cron-gated rather than a fixed daemon interval. **See inline comment in `docs/ANTI_CHEAT_AND_SECURITY.md` §8.2** — flagged as an option for later, not yet adopted into the schema. |
| **Contest Toolchain & Package Manifests** | [`icpc-environment/icpc-env`](https://github.com/icpc-environment/icpc-env), [`maratona-linux/maratona-team-tools`](https://github.com/maratona-linux/maratona-team-tools), [`ioi-2025/contestant-vm`](https://github.com/ioi-2025/contestant-vm) | `icpc-env`: `MIT`, `maratona`: `GPL-2.0`, `contestant-vm`: `GPL-2.0` | [`ROADMAP.md` Phase 6](../ROADMAP.md#phase-6-software-toolchains-virtual-appliances--cicd-ga-release), [`docs/COMPARATIVE_ANALYSIS.md`](./docs/COMPARATIVE_ANALYSIS.md) | N/A | 🟡 Evaluated | Package lists, compiler flags, and editor plugins cross-referenced to ensure 1:1 parity with international contest standards. Note: `icpc-env`'s Kotlin is not an apt package — it's vendored as a manual `.zip` release under `/opt/kotlinc`, a pattern GallosOS's `.gsm` module packaging should account for. |
| **CDN-Judge Traffic Interception (Squid/nginx TLS-termination)** | [`icpc-environment/icpc-env`](https://github.com/icpc-environment/icpc-env), [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) | Both `MIT` | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) §3.4, [`docs/COMPARATIVE_ANALYSIS.md`](./COMPARATIVE_ANALYSIS.md) §9.1 | N/A (Not adopted) | 🟡 Evaluated | **Idea for later, not adopted; independently corroborated by two sources.** `icpc-env`'s `files/squid/squid.conf.j2` (`ssl_bump bump all` + system-wide CA) and `files/nginx.conf.j2` do full transparent MITM interception, but `icpc-env` itself has been dormant since 2024-10-03. The actively-maintained `icpcsysops/ansible` (pushed 2026-03-25) independently built `roles/reverseproxy` — a per-domain TLS-terminating nginx proxy reached via `/etc/hosts` redirection — and reserves a dedicated `squidserver` host in its example inventory (its config is not present in the tree available for inspection). Both close the SNI/CDN-IP-sharing gap `nftables` can't, at the cost of trusting a proxy in the TCB and installing/trusting a cert — no decision made yet for GallosOS. |
| **Per-Service Firewall Rule Granularity** | [`icpcsysops/ansible`](https://github.com/icpcsysops/ansible) (`do_iptables.yml` / `roles/iptablesrules/templates/team.iptables.rules.j2`) | `MIT` (confirmed) | [`docs/ANTI_CHEAT_AND_SECURITY.md`](./ANTI_CHEAT_AND_SECURITY.md) §3.1 | N/A (Idea for later) | 🟡 Evaluated | **Idea for later, not adopted.** The real World Finals ruleset scopes every service to its own explicit `/32` + port rule (judge, NTP, backup SSH, printing) rather than a shared "internal services" set — GallosOS's telemetry-block port/IP list already matches this file almost verbatim, but the internal-services set could be split into per-service rules to match more closely. Flagged, not implemented. |

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
