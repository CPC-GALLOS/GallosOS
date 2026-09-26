"""Control the host mount service from the sandboxed GallosOS daemon."""

import subprocess

EVENT_DATA_MOUNTPOINT = "/media/event-data"
SERVICE = "gallos-event-storage.service"


def _host_source() -> str | None:
    result = subprocess.run(
        ["findmnt", "-N", "1", "-rn", "-M", EVENT_DATA_MOUNTPOINT, "-o", "SOURCE"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def mount_event_data() -> bool:
    """Start the root host service; return whether the optional partition exists."""
    result = subprocess.run(
        ["systemctl", "start", SERVICE],
        capture_output=True,
        text=True,
        check=False,
        timeout=35,
    )
    if result.returncode != 0:
        raise RuntimeError(f"event-data service failed: {result.stderr.strip()}")
    return _host_source() is not None


def unmount_event_data() -> None:
    """Fail if event-data is still mounted after the host service stops."""
    if _host_source():
        # A busy ExecStop leaves the mount present but the oneshot unit in a
        # failed state. Starting it again validates/rearms that mount so a
        # later retry can actually run ExecStop.
        rearmed = subprocess.run(
            ["systemctl", "start", SERVICE],
            capture_output=True,
            text=True,
            check=False,
            timeout=35,
        )
        if rearmed.returncode != 0:
            raise RuntimeError(f"event-data rearm failed: {rearmed.stderr.strip()}")
    result = subprocess.run(
        ["systemctl", "stop", SERVICE],
        capture_output=True,
        text=True,
        check=False,
        timeout=35,
    )
    if result.returncode != 0 or _host_source():
        raise RuntimeError(f"event-data unmount failed: {result.stderr.strip()}")
