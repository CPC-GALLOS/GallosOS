"""Trusted local TOML ingestion and validation for the GallosOS daemon."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tomllib
from jsonschema import Draft7Validator

UTC_TZ_OFFSET = "+00:00"

DEFAULT_CONFIG: dict[str, Any] = {
    "version": "1.0",
    "mode": "Default",
    "global": {
        "event_name": "GallosOS Live Session",
        "timezone": "UTC",
        "keyboard_layout": "us",
    },
    "default": {
        "allow_internet": True,
        "allow_usb_storage": True,
        "wallpaper_url": "",
    },
    "contest": {
        "allowed_websites": [],
        "allowed_tcp_ports": [80, 443],
        "allow_usb_storage": False,
        "wallpaper_url": "",
    },
    "event": {
        "allow_internet": True,
        "allow_usb_storage": True,
    },
    "recovery": {
        "root_password_hash": None,
    },
}


CONFIG_SEARCH_DIRECTORIES = [
    "/etc/gallos",
    "/boot/gallos/config",
    "/boot/gallos",
    "/gallos",
    "/usr/share/gallos",
]

_PACKAGED_SCHEMA = Path(__file__).resolve().parent / "directives.schema.json"
SCHEMA_PATH = (
    _PACKAGED_SCHEMA
    if _PACKAGED_SCHEMA.is_file()
    else Path(__file__).resolve().parents[2] / "schema" / "directives.schema.json"
)


def validate_directives(config: dict[str, Any]) -> None:
    """Reject invalid organizer policy before any active state is changed."""
    with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    error = next(Draft7Validator(schema).iter_errors(config), None)
    if error is not None:
        location = ".".join(str(part) for part in error.absolute_path) or "root"
        raise ValueError(f"Invalid directives at {location}: {error.message}")


def _discover_unique_profile(dirs: list[str], suffix: str) -> str | None:
    """Finds a single profile matching suffix across search directories if unambiguous."""
    discovered: list[str] = []
    seen: set[str] = set()
    for d in dirs:
        if not os.path.isdir(d):
            continue
        try:
            for entry in sorted(os.listdir(d)):
                if entry.endswith(suffix) and entry != suffix.lstrip("."):
                    full_path = os.path.join(d, entry)
                    real = os.path.realpath(full_path)
                    if os.path.isfile(full_path) and real not in seen:
                        seen.add(real)
                        discovered.append(full_path)
        except OSError as e:
            print(f"[config] Warning reading directory {d}: {e}", file=sys.stderr)

    if len(discovered) == 1:
        return discovered[0]
    if len(discovered) > 1:
        print(
            f"[config] Multiple profiles with {suffix} found ({len(discovered)}); "
            "provide one profile or an Organizer canonical gallos.toml.",
            file=sys.stderr,
        )
    return None


def load_local_config(search_dirs: list[str] | None = None) -> tuple[dict[str, Any] | None, str]:
    """Finds and loads the primary local gallos.toml config file.

    Prefers an organizer's canonical file, then one named profile, then the
    baseline/baseline.gallos.toml bundled with the ISO.
    """
    dirs = search_dirs if search_dirs is not None else CONFIG_SEARCH_DIRECTORIES
    # 1. Exact gallos.toml matches in priority order
    for d in dirs:
        candidate = os.path.join(d, "gallos.toml")
        if os.path.isfile(candidate):
            try:
                with open(candidate, "rb") as f:
                    data = tomllib.load(f)
                print(f"[config] Loaded local configuration from {candidate}")
                return data, candidate
            except Exception as e:
                raise ValueError(f"Failed to parse canonical configuration {candidate}: {e}") from e

    # 2. Single *.gallos.toml auto-discovery fallback
    discovered = _discover_unique_profile(dirs, ".gallos.toml")
    if discovered:
        try:
            with open(discovered, "rb") as f:
                data = tomllib.load(f)
            print(f"[config] No canonical gallos.toml found; auto-loaded profile: {discovered}")
            return data, discovered
        except Exception as e:
            raise ValueError(f"Failed to parse profile {discovered}: {e}") from e

    # 3. The ISO baseline must not shadow a profile added by an organizer.
    for d in dirs:
        candidate = os.path.join(d, "baseline", "baseline.gallos.toml")
        if os.path.isfile(candidate):
            try:
                with open(candidate, "rb") as f:
                    data = tomllib.load(f)
                print(f"[config] Loaded bundled baseline from {candidate}")
                return data, candidate
            except Exception as e:
                raise ValueError(f"Failed to parse bundled baseline {candidate}: {e}") from e

    return None, ""


def load_machine_config(search_dirs: list[str] | None = None) -> dict[str, Any]:
    """Finds and loads per-machine machine.toml configuration if present."""
    dirs = search_dirs if search_dirs is not None else CONFIG_SEARCH_DIRECTORIES[:4]
    # 1. Exact machine.toml matches
    for d in dirs:
        candidate = os.path.join(d, "machine.toml")
        if os.path.isfile(candidate):
            try:
                with open(candidate, "rb") as f:
                    data = tomllib.load(f)
                print(f"[config] Loaded machine identity from {candidate}")
                return data
            except Exception as e:
                print(f"[config] Failed to parse {candidate}: {e}", file=sys.stderr)

    # 2. Single *.machine.toml fallback
    discovered = _discover_unique_profile(dirs, ".machine.toml")
    if discovered:
        try:
            with open(discovered, "rb") as f:
                data = tomllib.load(f)
            print(f"[config] Auto-loaded discovered machine identity: {discovered}")
            return data
        except Exception as e:
            print(f"[config] Failed to parse machine identity {discovered}: {e}", file=sys.stderr)

    return {}


def is_config_expired(config: dict[str, Any]) -> bool:
    """Checks if the global.config_expiration timestamp has passed."""
    global_cfg = config.get("global", {})
    exp_str = global_cfg.get("config_expiration")
    if not exp_str:
        return False
    try:
        normalized = exp_str.replace("Z", UTC_TZ_OFFSET)
        exp_dt = datetime.fromisoformat(normalized)
        now_dt = datetime.now(timezone.utc)
        if now_dt > exp_dt:
            print(f"[config] Configuration expired at {exp_dt} (Current: {now_dt})")
            return True
    except Exception as e:
        print(f"[config] Error parsing config_expiration '{exp_str}': {e}", file=sys.stderr)
    return False


def _load_local_recovery_hash() -> str | None:
    """Loads recovery.root_password_hash from local directives only.

    Deliberately never sourced from a remotely-fetched config: gallos.toml can be
    hosted on a shared Gist/server (see fetch_remote_config above), and a root
    password hash traveling through and resting in that file would defeat the
    point of keeping it secret. See docs/ROOT_ACCESS.md.
    """
    local_data, _ = load_local_config()
    if local_data:
        return local_data.get("recovery", {}).get("root_password_hash")
    return None


def load_active_config() -> dict[str, Any]:
    """Load trusted local directives; kernel arguments cannot replace Organizer policy."""
    config_data, source_name = load_local_config()

    if config_data is not None:
        validate_directives(config_data)
    else:
        print("[config] No external config found. Using default profile.")
        config_data = DEFAULT_CONFIG.copy()
        source_name = "default internal"

    if is_config_expired(config_data):
        print("[config] WARNING: Config is expired! Reverting to Default mode.")
        config_data["mode"] = "Default"

    # Always re-sourced from local-only, regardless of config_data's own origin above —
    # a fresh dict assignment, never a mutation of a dict that might alias DEFAULT_CONFIG.
    config_data["recovery"] = {"root_password_hash": _load_local_recovery_hash()}

    print(f"[config] Active configuration source: {source_name}")
    return config_data
