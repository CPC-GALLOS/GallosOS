"""Atomic runtime record for mode transitions across daemon restarts."""

import contextlib
import json
import os
import pathlib
import tempfile

RECORD = pathlib.Path("/run/gallos/transition.json")
MODES = {"Contest", "Event", "Default"}


def write_record(mode: str, target_mode: str, status: str, error: str) -> None:
    RECORD.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(RECORD.parent, 0o755)  # noqa: S103
    payload = {
        "mode": mode,
        "target_mode": target_mode,
        "transition_status": status,
        "last_error": error,
    }
    fd, path = tempfile.mkstemp(dir=RECORD.parent, prefix=".transition-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o644)
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(path, RECORD)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def read_record() -> dict[str, str] | None:
    try:
        with RECORD.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {
            "mode": "Unknown",
            "target_mode": "Unknown",
            "transition_status": "error",
            "last_error": "Invalid transition record",
        }
    if payload.get("mode") not in MODES or payload.get("target_mode") not in MODES:
        return {
            "mode": "Unknown",
            "target_mode": "Unknown",
            "transition_status": "error",
            "last_error": "Invalid transition record",
        }
    if payload.get("transition_status") == "pending":
        payload["transition_status"] = "error"
        payload["last_error"] = "Transition interrupted by daemon restart"
    return payload
