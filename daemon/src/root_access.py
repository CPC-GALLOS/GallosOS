"""Apply a local recovery hash through a dedicated host service."""

import subprocess

SERVICE = "gallos-root-access.service"


def apply_local_root_password() -> None:
    """Run the host helper, which reads the trusted local configuration."""
    result = subprocess.run(
        ["systemctl", "start", SERVICE],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"root recovery service failed: {result.stderr.strip()}")


def set_root_password(password_hash: str | None) -> None:
    """Applies the configured root password hash, or re-locks root if unset."""
    if password_hash:
        print("[root_access] Applying configured root password hash for local su recovery.")
        subprocess.run(
            ["chpasswd", "-e"],
            input=f"root:{password_hash}\n",
            text=True,
            check=True,
        )
    else:
        print("[root_access] No root password hash configured; keeping root locked.")
        subprocess.run(["passwd", "-l", "root"], check=True)
