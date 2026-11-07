# Casper Boot Integration

## Overview

This directory contains an adapted Casper bottom hook and GallosOS's build-time
overlay patch. Preserve the attribution and licensing recorded in
[UPSTREAM.md](./UPSTREAM.md) and [LICENSE](./LICENSE).

## Interface

- [55gallos-live](./55gallos-live): `prereqs` entry point and normal Casper
  bottom-hook execution; expects `rootmnt`, `casper-functions`, and `casper-helpers`.
- [casper-gsm-overlay.sh](./casper-gsm-overlay.sh): takes the installed Casper
  script path as its positional argument (`CASPER_SCRIPT`). The build invokes it
  from `build/scripts/02-provision.sh`.
- [casper-gsm-overlay.insert.sh](./casper-gsm-overlay.insert.sh): companion
  fragment inserted into Casper's `setup_overlay()`; it uses that function's
  `image_directory`, `croot`, `roopt`, `rofsstring`, and `rofslist` variables.
  It is not a standalone executable.

## Invariants

- `casper-gsm-overlay.sh:BACKDEV_REPLACEMENT` adds `.gsm` handling to the backing
  device case; `LOOP_ANCHOR` locates insertion before the overlay layer list is
  finalized. This runs earlier than the bottom hook.
- `casper-gsm-overlay.insert.sh:gallos_module_image` processes the regular
  module glob and prepends each layer. Later-expanded modules take priority;
  `gallos_custom_layer` (`gallos/system/99-custom.gsm`) is processed last and
  prepended above them. Unknown filesystem types and failed mounts call `panic`.
- The fragment mounts the detected filesystem type; it does not independently
  restrict module contents to SquashFS.
- Patch preflight uses substring checks, but `awk` replacements require exact
  lines. It does not verify replacement counts, and normal reapplication to an
  already patched file fails the original backing-device anchor check.
- `55gallos-live` creates `/boot/gallos` only when the boot medium's `gallos`
  directory exists and the target does not. It does not manage event-data or
  implement `toram`; those belong to runtime storage and upstream Casper.

## Side Effects

- `55gallos-live:rootmnt` creates a missing contestant home, attempts ownership
  `1000:1000`, and exposes `/cdrom/gallos` through a `/boot/gallos` symlink.
- The patcher writes a sibling `.gallos-tmp` file and replaces `CASPER_SCRIPT`.
- The inserted fragment creates mountpoints, mounts images with `ro,noatime`,
  and mutates the overlay layer lists used by Casper.

## Verification

From the repository root:

```bash
./scripts/check.sh
```

The gate does not directly ShellCheck these vendored hooks. Its passing result
does not establish initramfs or layer-order behavior on a booted image; use the
separate image validation workflow in `build/scripts/README.md`.
