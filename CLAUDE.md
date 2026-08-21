# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status: specification phase, not an implementation

GallosOS is a Linux Live distribution for competitive-programming contests (ICPC, IOI, OMI, Maratona SBC), designed as a modern replacement for huronOS. **The repository currently contains only architecture, specs, and example configs — no daemon code, build scripts, or ISO tooling exist yet.** Everything here (`build.toml` pipeline, `gallos-daemon`, `gallos-flash`, `gallos-convert`, `gallos-config-builder`) is planned, not implemented. Do not write code claiming these tools exist or write about GallosOS as if it has been hardware-tested — see the non-negotiable rules below.

There are no build, lint, or test commands in this repo yet. The only "validation" surface today is TOML schema-checking `examples/*.toml` / `gallos.toml` files against `schema/directives.schema.json` (wired up via `.taplo.toml` and VS Code's `tamasfe.even-better-toml` extension — `taplo lint`/`taplo check` if the CLI is available).

## Non-negotiable rules (from AGENTS.md — read it in full before substantial work)

- **English only.** All docs, comments, schema descriptions, and commit messages.
- **Zero hallucination.** Every package name, version, compiler flag, or claim must be grounded in local reference trees (see below) or real upstream sources. Never fabricate links or use placeholder domains.
- **Never claim empirical validation.** No implying hardware benchmarks, write-speed tests, or lab trials have occurred — GallosOS is architectural/conceptual only right now. Frame comparisons as derived from binary/source inspection.
- **Cross-document coherence.** Terminology, directory layouts, and mode-precedence rules must stay synchronized across `README.md`, `ROADMAP.md`, `docs/`, `examples/`, and `schema/`. A change to one often requires updating the others.
- **Canonical terms** (defined in `README.md` § Terminology): **Contestant** (never "participant" as primary), **Organizer**, **Venue Controller** (optional, Tier 3 only — never assume it exists), **Judge Server** (external, e.g. BOCA/DOMjudge/CMS/omegaUp — GallosOS never hosts it).
- **In-band vs out-of-band tooling split:** anything running inside the live contest OS (`gallos-daemon`, hooks) must be Bash/Python for field-hackability without a compiler; anything the organizer runs on their own host (`gallos-flash`, `gallos-convert`) must be a statically compiled Rust binary.
- **Infrastructure-agnostic.** Never assume a Venue Controller, internet connectivity, or specific network services are present — GallosOS spans a 5-tier spectrum from fully air-gapped to institutionally managed.

## Repository layout

```
GallosOS/
├── AGENTS.md                  # Full agent/contributor ruleset — canonical source of the rules above
├── README.md                  # Project overview, MVP scope, terminology, key pillars
├── ROADMAP.md                 # Phase 1–7 engineering checklist (Alpha → GA → post-GA)
├── docs/
│   ├── ARCHITECTURE.md        # OverlayFS/SquashFS layering, Wayland kiosk, build & VM testing
│   ├── CONFIG_SPEC.md         # gallos.toml directive spec, Config Builder, mode hierarchy, .hdf migration
│   ├── BUILD_SYSTEM.md        # build.toml spec, the 4-stage containerized build pipeline
│   ├── WAYLAND_DESKTOP.md     # Labwc/Waybar/Foot/Mako desktop spec, keybindings
│   ├── HARDWARE_COMPATIBILITY.md
│   ├── ANTI_CHEAT_AND_SECURITY.md  # nftables threat model, USB lock, telemetry stripping
│   ├── COMPARATIVE_ANALYSIS.md     # GallosOS vs HuronOS vs Maratona vs ICPC-Env vs IOI-VM
│   └── PROVENANCE.md          # Third-party vendoring ledger, license tracking
├── examples/*.toml            # Production-ready gallos.toml profiles per contest archetype (see examples/README.md)
└── schema/directives.schema.json  # JSON Schema (draft-07) validating gallos.toml
```

`HuronOS/`, `maratona-linux/`, `icpc-env/`, `contestant-vm/`, and `ansible/` are present on disk but **gitignored** — they are local upstream reference trees kept only for cross-referencing real package names/versions/patterns when writing specs. Never edit them, and never assume they exist in a checkout other than this one.

## Core architectural concepts

**The three-file config split** (see `docs/BUILD_SYSTEM.md` § "Holy Trinity"):
- `build.toml` — build-time only, feeds the (planned) `gallos-builder` container to produce a custom ISO.
- `gallos.toml` — run-time global contest policy (identical across all workstations): schedule windows, judge whitelist, allowed software, printing mode, branding.
- `machine.toml` — run-time per-workstation identity: hostname, room, team, seat label.

`examples/*.toml` are templates to be copied to `gallos.toml`, not consumed directly.

**Mode hierarchy** (strict precedence, defined in `docs/CONFIG_SPEC.md`):
`Contest ≻ Event ≻ Default`. Contest = strict lockdown/judge-only network/fresh isolation. Event = training-camp mode with persistent workspace, hidden the instant a Contest window starts. Default = fallback when no window is active. Any feature touching scheduling, firewall rules, or desktop state must respect this precedence.

**Storage model:** immutable read-only base SquashFS + modular `.gsm` software packages, unioned via OverlayFS with an ephemeral `tmpfs` upper layer — the machine returns to a pristine state on reboot. Contestants export code manually to USB at contest end.

**Hybrid mono/poly-repo strategy** (`AGENTS.md` § Organization-Wide Repository Map): this repo holds the core build pipeline, docs, and configs. Standalone organizer tools with independent release cycles (`gallos-flash`, `gallos-convert`, `gallos-config-builder`) live in sibling repos under the `CPC-GALLOS` GitHub org and are only *planned* — do not assume their code is reachable from here.

## Working on docs and examples

- When adding/editing an `examples/*.toml` profile, keep the `#:schema` header pointing at `schema/directives.schema.json` and validate structurally against it (see `software_list` pattern `^(internet|langs|programming|tools|docs)/[a-z0-9_+-]+$`, `iso8601_datetime` format, etc.).
- Schema changes in `schema/directives.schema.json` must be reflected in `docs/CONFIG_SPEC.md` and, if directive names change, in every `examples/*.toml`.
- New roadmap items belong in the correct `ROADMAP.md` phase (Phase 1–3 = MVP; Phase 4+ is explicitly post-MVP polish) — don't scope-creep the MVP phases.
