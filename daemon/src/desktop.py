"""Desktop integration module for GallosOS Daemon.

Manages wallpaper transitions via swaybg, sends high-priority notifications
via Mako, and exports real-time status state for Waybar custom modules.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WALLPAPER_STATE = Path("/run/gallos/wallpaper.json")


def update_wallpaper(mode: str, custom_url: str = "") -> None:
    """Publish a local asset for the consumer running inside the Wayland session."""
    fallback = f"/usr/share/backgrounds/gallos/{'contest' if mode == 'Contest' else 'default'}.png"
    path = fallback
    if custom_url and custom_url != "default":
        if os.path.isfile(custom_url) and os.access(custom_url, os.R_OK):
            path = str(Path(custom_url).resolve())
        else:
            print(
                f"[desktop] Wallpaper unavailable: {custom_url!r}; using fallback", file=sys.stderr
            )
    WALLPAPER_STATE.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=WALLPAPER_STATE.parent, prefix=".wallpaper-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o644)
            json.dump({"path": path, "fallback": fallback}, stream)
        os.replace(temporary, WALLPAPER_STATE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def send_desktop_notification(title: str, message: str, urgency: str = "normal") -> None:
    """Dispatches a desktop notification to Mako."""
    print(f"[desktop] Notification [{urgency}]: {title} - {message}")
    try:
        notify_body = f"notify-send -u {urgency} -a GallosOS '{title}' '{message}'"
        cmd = ["su", "-", "contestant", "-c", notify_body]
        subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"[desktop] Error sending notification: {e}", file=sys.stderr)


def export_waybar_state(
    mode: str, remaining_seconds: int = 0, transition_status: str = "ready", last_error: str = ""
) -> None:
    """Writes /run/gallos/state.json for Waybar custom status modules."""
    os.makedirs("/run/gallos", exist_ok=True)
    state_file = "/run/gallos/state.json"

    if remaining_seconds > 0:
        mins, secs = divmod(remaining_seconds, 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
    else:
        time_str = "Standby"

    payload = {
        "mode": mode,
        "badge": f"MODE: {mode.upper()}",
        "time_str": time_str,
        "remaining_sec": remaining_seconds,
        "transition_status": transition_status,
        "last_error": last_error,
    }

    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.chmod(state_file, 0o644)
    except Exception as e:
        print(f"[desktop] Error writing state.json: {e}", file=sys.stderr)
