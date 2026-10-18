"""Delegate volatile scratch cleanup outside gallosd's read-only mounts."""

import subprocess


def reset_contest_scratch() -> None:
    result = subprocess.run(
        ["systemctl", "start", "gallos-clean-state.service"],
        check=False,
        capture_output=True,
        text=True,
        timeout=185,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Contest scratch reset failed: {result.stderr.strip()}")
