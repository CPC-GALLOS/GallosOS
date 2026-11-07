# Vendored Integrations

## Overview

This subtree holds inherited integration code and its attribution records.
The repository-wide provenance ledger is `docs/PROVENANCE.md`.

## Subdirectories & Boundaries

- [inherited](./inherited/README.md): Casper boot integration and a contestant
  storage authorization rule, with per-package provenance and license files.

## Interface

The build consumes `inherited/maratona-casper/55gallos-live`, the
`casper-gsm-overlay.sh:CASPER_SCRIPT` patch entry point, and the
`99-gallos-usb-block.rules:polkit.addRule` callback. Their detailed contracts
are indexed by [inherited](./inherited/README.md).

## Invariants

Boot integration and storage authorization remain separate components.
The Polkit callback does not select GallosOS modes; its installer controls
policy scope. Keep the per-package `UPSTREAM.md` and `LICENSE` records with
these files when redistributing them.

## Side Effects

When invoked or installed, children patch Casper, create boot paths, mount
overlay layers, and register an authorization rule. There is no top-level
vendor process or automatic activation from this directory alone.

## Verification

Run `./scripts/check.sh` from the repository root. Consult child contracts for
coverage limits; this repository gate does not replace boot or policy acceptance.
