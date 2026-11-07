# Contestant Storage Authorization Rule

## Overview

This directory contains the adapted Polkit authorization rule described in
[UPSTREAM.md](./UPSTREAM.md). Preserve its [LICENSE](./LICENSE) and attribution.

## Interface

[99-gallos-usb-block.rules](./99-gallos-usb-block.rules) registers
`polkit.addRule(function(action, subject) ...)`. It returns `polkit.Result.NO`
when `action.id` starts with `org.freedesktop.udisks2.` and `subject.user` is
`contestant`.

## Invariants

- The predicate covers all matching UDisks2 actions for that user, not only
  USB devices. Other actions and users receive no result from this callback.
- The rule itself does not inspect the current mode or Organizer configuration.
  `build/scripts/03-harden.sh:allow_usb_storage` conditionally installs this
  file when the build setting is `false`.
- Runtime policy has a separate owner: `daemon/src/usb_manager.py:set_usb_storage_allowed`
  invokes a host service; `daemon/src/usb_storage_host.py:apply_usb_policy`
  installs or removes an equivalent live rule. Source presence is not proof
  of effective authorization behavior on a running image.

## Side Effects

Loading the installed file registers a Polkit authorization callback. The file
itself performs no mounts, device removal, or installation; installation and
runtime replacement are performed by the build/runtime helpers above.

## Verification

From the repository root:

```bash
./scripts/check.sh
```

The gate tests runtime USB helpers but does not exercise a live Polkit/UDisks2
authorization decision. Verify installed policy separately on the target image.
