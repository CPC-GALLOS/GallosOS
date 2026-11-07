# Organizer Directives Schema

## Overview

[directives.schema.json](./directives.schema.json) describes the accepted shape
of `gallos.toml`. It includes both runtime-consumed fields and explicitly planned
capabilities; accepting a field does not implement it.

## Interface

- `directives.schema.json:$schema`: JSON Schema Draft-07.
- `properties`: `global`, `branding`, `recovery`, `default`, `event`, `contest`,
  `machines`, and `printing` are the top-level settings.
- `definitions.mode_config`: shared website/device, wallpaper, schedule/timer,
  software, browser-policy, audit, printing, and announcement shape.
- `definitions`: reusable time windows, bookmarks, website/software lists,
  and planned audit, printing, and broadcast structures.

The runtime consumer is `daemon/src/config.py`; the repository validator is
`scripts/validate_toml.py`. The profile catalog is `examples/README.md`.

## Invariants

- Root `required` demands `global`; `properties.global.required` demands
  `timezone`. Declared object schemas reject unknown properties through
  `additionalProperties: false`.
- `definitions.mode_config.properties.duration_minutes` accepts integers from
  1 through 1440. MAC addresses require lowercase colon-separated hexadecimal;
  declared checksums and broadcast keys require 64 lowercase hexadecimal characters.
- `definitions.iso8601_datetime` checks string shape, not calendar validity.
  `definitions.time_window` does not compare start and end; timezone and website
  strings are not semantically validated here.
- The remote-wallpaper checksum requirement is descriptive text, not a
  conditional schema constraint. Recovery hashes are typed as strings only.
- `default` values are metadata. The descriptions explicitly mark fields such
  as software switching, audio, bookmarks, audit, printing, broadcasts, and
  keyboard settings as planned or unconsumed. The global mode-enable flags
  must not be treated as enforcement controls; see the runtime contract in
  `daemon/src/README.md` and `ROADMAP.md` for implementation boundaries.

## Side Effects

None in this declarative file. Validation checks supplied data; it does not
install software, apply defaults, change passwords, or enforce network/device policy.

## Verification

From the repository root with `jsonschema` installed:

```bash
python3 scripts/validate_toml.py
./scripts/check.sh
```

Inspect validator output for `syntax + schema`; unavailable schema support can
fall back to syntax-only checks. Runtime and Live-image acceptance are separate.
