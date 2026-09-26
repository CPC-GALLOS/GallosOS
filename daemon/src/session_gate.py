"""Gate tty1 contestant access around policy transitions."""

import pathlib
import subprocess

READY_MARKER = pathlib.Path("/run/gallos/kiosk-ready")


def _systemctl(action: str, unit: str) -> None:
    result = subprocess.run(
        ["systemctl", action, unit],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{action} {unit} failed: {result.stderr.strip()}")


def stop_kiosk() -> None:
    """Stop the login service and every existing contestant process."""
    READY_MARKER.unlink(missing_ok=True)
    stop_error = None
    try:
        _systemctl("stop", "getty@tty1.service")
    except RuntimeError as exc:
        stop_error = exc
    result = subprocess.run(
        ["pkill", "-KILL", "-u", "contestant"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"contestant session termination failed: {result.stderr.strip()}")
    if stop_error is not None:
        raise stop_error


def start_recovery_console(enabled: bool) -> None:
    """Offer a root password prompt on tty1 only when a hash is configured."""
    if enabled:
        _systemctl("start", "gallos-recovery-console.service")


def release_kiosk() -> None:
    """Replace the recovery prompt with the contestant kiosk."""
    _systemctl("stop", "gallos-recovery-console.service")
    READY_MARKER.parent.mkdir(parents=True, exist_ok=True)
    READY_MARKER.touch(mode=0o600)
    try:
        _systemctl("start", "getty@tty1.service")
    except Exception:
        READY_MARKER.unlink(missing_ok=True)
        raise
