# Repository Verification Scripts

## Overview

These developer tools check repository source and configuration. They do not
build an ISO or apply Organizer policy to a workstation.

## Interface

- [check.sh](./check.sh): runs Ruff lint/format checks, daemon and build tests,
  ShellCheck, TOML validation, and commit-message validation. `REPO_ROOT` is
  derived from the script location, so this wrapper normalizes its working directory.
- [check_commits.py](./check_commits.py): `validate_commit_message()` returns
  `(valid, reason)`. `parse_args()` exposes `--msg`, `--file`, `--ci`, `--range`,
  `--last`, and `--strict`; `resolve_commits()` uses that selection order.
- [validate_toml.py](./validate_toml.py): `main()` scans fixed repository-root,
  example, and build-profile globs, parses TOML, and optionally applies
  `schema/directives.schema.json` to directives files.

## Invariants

- Invoke the Python scripts from the repository root: TOML discovery/schema
  lookup and Git revision lookup use the caller's working directory.
- `check.sh:FAILED` aggregates failed checks. Missing ShellCheck is reported
  as a skip; installed Taplo selects `taplo check`, otherwise the Python TOML
  validator runs. Inspect the output as well as the exit status.
- `validate_toml.py:HAS_JSONSCHEMA` makes schema validation conditional on the
  dependency and a loadable schema. Without those, validation is syntax-only.
  Build profiles receive syntax checks; files under `examples/` receive
  directives checks when the schema is available. No matching files succeeds.
  This script imports `tomllib` directly and needs Python 3.11 or newer.
- `check_commits.py:validate_commit_message()` checks header shape, allowed
  type, and header/body separation. `--strict` disables automated merge/revert
  exemptions. The checker does not enforce every editorial rule in `AGENTS.md`,
  including imperative mood and lowercase subjects.
- `check_commits.py:main()` succeeds when selection returns no commits, including
  some Git errors or a missing `--file`. Default selection checks commits ahead
  of upstream, falling back to HEAD; it is not a whole-history audit.

## Side Effects

The Python validators read local files/Git history and print diagnostics.
`check.sh` launches external tools and tests, which can create test and tool
caches. It uses `ruff format --check`, not the formatting command that edits source.

## Verification

From the repository root:

```bash
./scripts/check.sh
```

`daemon/tests/test_check_commits.py` covers commit validation;
`build/tests/test_developer_tasks.py` covers task wiring. These checks provide
source/unit evidence, not booted-image, graphical, or physical acceptance.
