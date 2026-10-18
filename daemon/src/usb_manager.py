"""Request USB policy changes in the host mount namespace."""

import subprocess

SERVICE = "gallos-usb-storage@{}.service"


def set_usb_storage_allowed(allowed: bool) -> None:
    """Wait for host enforcement before permitting the mode transition."""
    action = "unlock" if allowed else "lock"
    result = subprocess.run(
        ["systemctl", "start", SERVICE.format(action)],
        check=False,
        capture_output=True,
        text=True,
        timeout=95,
    )
    if result.returncode != 0:
        raise RuntimeError(f"USB {action} failed: {result.stderr.strip()}")
