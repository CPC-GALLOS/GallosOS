#!/usr/bin/env python3
"""Read one dotted key out of a build.toml file for the shell pipeline stages.

Usage: tomlget.py <file.toml> <section.key>

Scalars print as-is (booleans as "true"/"false"). Lists print one item per
line so callers can `mapfile -t arr < <(tomlget.py ...)`. A missing key
prints nothing and exits 0 — stage scripts treat that as "no directive".
"""

import sys

import tomllib


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: tomlget.py <file.toml> <section.key>", file=sys.stderr)
        return 2

    path, dotted_key = sys.argv[1], sys.argv[2]
    with open(path, "rb") as f:
        data = tomllib.load(f)

    value = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return 0
        value = value[part]

    if isinstance(value, list):
        for item in value:
            print(item)
    elif isinstance(value, bool):
        print("true" if value else "false")
    elif value is not None:
        print(value)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130) from None
