# Inherited Runtime Integrations

## Overview

These integration packages preserve their local provenance and license files.
They are consumed by the image build; this directory has no standalone launcher.

## Subdirectories & Boundaries

- [Casper boot integration](./maratona-casper/README.md): bottom hook and
  build-time overlay patch.
- [Storage authorization rule](./maratona-usuario-icpc/README.md): Polkit
  callback for contestant UDisks2 actions.

## Interface

`maratona-casper/casper-gsm-overlay.sh:CASPER_SCRIPT` is the patcher's input;
`maratona-casper/55gallos-live:prereqs` is the initramfs hook interface.
`maratona-usuario-icpc/99-gallos-usb-block.rules:polkit.addRule` is loaded by
Polkit when installed. See the child contracts for inputs and installation owners.

## Invariants

The Casper fragment runs inside `setup_overlay()` before the bottom hook.
The Polkit callback has no mode-selection logic; build/runtime helpers scope
its installation. Preserve the distinctions and attribution recorded in each
child's `UPSTREAM.md` and `LICENSE`.

## Side Effects

The Casper patch replaces an installed script; boot hooks create paths and
mount overlay layers. The installed Polkit callback affects authorization.
Reading this directory does not activate either integration.

## Verification

Run `./scripts/check.sh` from the repository root. Child contracts identify
the limits of this source/unit gate and the separate runtime acceptance needs.
