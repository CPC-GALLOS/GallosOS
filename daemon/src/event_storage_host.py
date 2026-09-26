"""Host-namespace mount operations for the optional event-data partition."""

import os
import pwd
import subprocess
import sys

MOUNTPOINT = "/media/event-data"
WORKSPACE = f"{MOUNTPOINT}/contestant"


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, check=False, timeout=15)


def _mounted_source() -> str | None:
    result = _run("findmnt", "-rn", "-M", MOUNTPOINT, "-o", "SOURCE")
    return result.stdout.strip() if result.returncode == 0 else None


def mount_event_data() -> bool:
    """Return False when the optional partition is absent; otherwise mount it."""
    result = _run("blkid", "-o", "device", "-t", "LABEL=event-data")
    if result.returncode not in (0, 2):
        raise RuntimeError(f"event-data lookup failed: {result.stderr.strip()}")
    devices = result.stdout.splitlines()
    if not devices:
        if _mounted_source():
            raise RuntimeError("event-data is mounted but its label cannot be resolved")
        return False
    if len(devices) != 1:
        raise RuntimeError("more than one device has the event-data label")
    device = devices[0]
    fs_type = _run("blkid", "-s", "TYPE", "-o", "value", device)
    if fs_type.returncode != 0 or fs_type.stdout.strip() != "ext4":
        raise RuntimeError("event-data must be an ext4 partition")
    source = _mounted_source()
    if source:
        if os.path.realpath(source) != os.path.realpath(device):
            raise RuntimeError(f"unexpected device mounted at {MOUNTPOINT}: {source}")
    else:
        os.makedirs(MOUNTPOINT, exist_ok=True)
        mounted = _run("mount", "-t", "ext4", "-o", "nodev,nosuid", device, MOUNTPOINT)
        if mounted.returncode != 0:
            raise RuntimeError(f"event-data mount failed: {mounted.stderr.strip()}")
        if os.path.realpath(_mounted_source() or "") != os.path.realpath(device):
            raise RuntimeError("event-data mount is not visible in the host namespace")
    os.makedirs(WORKSPACE, mode=0o700, exist_ok=True)
    user = pwd.getpwnam("contestant")
    os.chown(WORKSPACE, user.pw_uid, user.pw_gid)
    os.chmod(WORKSPACE, 0o700)
    return True


def unmount_event_data() -> None:
    """Unmount synchronously so Contest cannot expose previous event files."""
    if not _mounted_source():
        return
    result = _run("umount", MOUNTPOINT)
    if result.returncode != 0:
        raise RuntimeError(f"event-data unmount failed: {result.stderr.strip()}")
    if _mounted_source():
        raise RuntimeError("event-data remained mounted")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"mount", "unmount"}:
        raise SystemExit("usage: event_storage_host.py mount|unmount")
    try:
        if sys.argv[1] == "mount":
            mount_event_data()
        else:
            unmount_event_data()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
