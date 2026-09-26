"""Config ingestion and validation module for GallosOS Daemon.

Handles hybrid config ingestion (remote URL with 5-second timeout,
fallback to local /boot/gallos/gallos.toml or /gallos/gallos.toml on Ventoy).
"""

import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

import tomllib

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


def get_cmdline_config_param() -> str | None:
    """Extracts gallos.config parameter from /proc/cmdline if present."""
    if not os.path.exists("/proc/cmdline"):
        return None
    try:
        with open("/proc/cmdline", encoding="utf-8") as f:
            cmdline = f.read()
        for token in cmdline.split():
            if token.startswith("gallos.config="):
                return token.split("=", 1)[1]
    except Exception as e:
        print(f"[config] Error reading /proc/cmdline: {e}", file=sys.stderr)
    return None


def fetch_remote_config(url: str, timeout_sec: int = 5) -> str | None:
    """Fetches remote gallos.toml content over HTTP/HTTPS with timeout."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        print(
            f"[config] Refusing non-HTTP(S) config scheme '{parsed.scheme}': {url}",
            file=sys.stderr,
        )
        return None

    print(f"[config] Fetching remote config from: {url} (timeout={timeout_sec}s)")
    req = urllib.request.Request(url, headers={"User-Agent": "GallosOS-Daemon/0.2.0"})  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            if resp.status == 200:
                return resp.read().decode("utf-8")
    except Exception as e:
        print(f"[config] Remote config fetch failed: {e}", file=sys.stderr)
    return None


CONFIG_SEARCH_DIRECTORIES = [
    "/boot/gallos/config",
    "/boot/gallos",
    "/gallos",
    "/etc/gallos",
    "/usr/share/gallos",
]


def resolve_config_path(target: str, search_dirs: list[str] | None = None) -> str | None:
    """Resolves a target filename or profile name against candidate directories.

    Accepts absolute paths, relative filenames, or profile names without extension
    (e.g., 'codeforces-training' -> 'codeforces-training.gallos.toml').
    """
    if os.path.isfile(target):
        return target

    dirs = search_dirs if search_dirs is not None else CONFIG_SEARCH_DIRECTORIES
    variants = [target]
    if not target.endswith(".toml"):
        variants.extend([f"{target}.gallos.toml", f"{target}.toml"])
    elif not target.endswith(".gallos.toml"):
        base = target.removesuffix(".toml")
        variants.append(f"{base}.gallos.toml")

    for d in dirs:
        for variant in variants:
            candidate = os.path.join(d, variant)
            if os.path.isfile(candidate):
                return candidate
    return None


def _load_cmdline_config(
    cmdline_target: str, search_dirs: list[str] | None = None
) -> tuple[dict[str, Any] | None, str]:
    """Loads configuration specified via kernel cmdline parameter."""
    parsed = urllib.parse.urlparse(cmdline_target)
    if parsed.scheme in ("http", "https"):
        raw_toml = fetch_remote_config(cmdline_target, timeout_sec=5)
        if raw_toml:
            try:
                return tomllib.loads(raw_toml), f"remote ({cmdline_target})"
            except Exception as e:
                print(f"[config] Failed to parse remote TOML: {e}", file=sys.stderr)
        return None, ""

    resolved_path = resolve_config_path(cmdline_target, search_dirs=search_dirs)
    if resolved_path:
        try:
            with open(resolved_path, "rb") as f:
                return tomllib.load(f), f"cmdline file ({resolved_path})"
        except Exception as e:
            print(f"[config] Error reading {resolved_path}: {e}", file=sys.stderr)

    return None, ""


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
            "specify via 'gallos.config=<profile>' or provide canonical file.",
            file=sys.stderr,
        )
    return None


def load_local_config(search_dirs: list[str] | None = None) -> tuple[dict[str, Any] | None, str]:
    """Finds and loads the primary local gallos.toml config file.

    Checks canonical gallos.toml locations first. If none is found, checks if
    exactly one *.gallos.toml profile is present across the search directories and
    auto-loads it.
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
                print(f"[config] Failed to parse {candidate}: {e}", file=sys.stderr)

    # 2. Single *.gallos.toml auto-discovery fallback
    discovered = _discover_unique_profile(dirs, ".gallos.toml")
    if discovered:
        try:
            with open(discovered, "rb") as f:
                data = tomllib.load(f)
            print(f"[config] No canonical gallos.toml found; auto-loaded profile: {discovered}")
            return data, discovered
        except Exception as e:
            print(f"[config] Failed to parse profile {discovered}: {e}", file=sys.stderr)

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
    """Loads recovery.root_password_hash from a local baked-in gallos.toml only.

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
    """Main entry point to obtain the active, validated configuration dictionary."""
    config_data: dict[str, Any] | None = None
    source_name = "built-in default"

    cmdline_target = get_cmdline_config_param()
    if cmdline_target:
        config_data, source_name = _load_cmdline_config(cmdline_target)

    if not config_data:
        config_data, source_name = load_local_config()

    if not config_data:
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
