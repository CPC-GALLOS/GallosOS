#!/usr/bin/env python3
"""Validates TOML syntax and schema for GallosOS configuration and example files."""

import glob
import json
import os
import sys

import tomllib

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def main() -> int:
    target_patterns = [
        "pyproject.toml",
        ".taplo.toml",
        "examples/*.gallos.toml",
        "examples/*.toml",
        "build/profiles/*.build.toml",
        "build/profiles/*.toml",
        "*.gallos.toml",
        "*.build.toml",
        "gallos.toml",
        "build.toml",
        "machine.toml",
    ]
    files = []
    for pattern in target_patterns:
        files.extend(glob.glob(pattern))

    files = sorted(set(files))
    if not files:
        print("[toml] No TOML files found to validate.")
        return 0

    schema_data = None
    schema_path = "schema/directives.schema.json"
    if HAS_JSONSCHEMA and os.path.isfile(schema_path):
        try:
            with open(schema_path, encoding="utf-8") as sf:
                schema_data = json.load(sf)
        except Exception as e:
            print(f"[toml] Warning: Failed to load JSON schema {schema_path}: {e}", file=sys.stderr)

    failed = False
    for filepath in files:
        try:
            with open(filepath, "rb") as f:
                data = tomllib.load(f)

            is_directives_file = filepath.endswith("gallos.toml") or filepath.startswith(
                "examples/"
            )
            if is_directives_file and schema_data and HAS_JSONSCHEMA:
                jsonschema.validate(instance=data, schema=schema_data)
                print(f"[toml] ✓ Validated {filepath} (syntax + schema)")
            else:
                print(f"[toml] ✓ Validated {filepath} (syntax)")
        except Exception as e:
            print(f"[toml] ✗ Validation error in {filepath}: {e}", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
