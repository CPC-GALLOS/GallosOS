"""Desktop integration module for GallosOS Daemon.

Manages wallpaper transitions via swaybg, sends high-priority notifications
via Mako, and exports real-time status state for Waybar custom modules.
"""

import json
import os
import subprocess
import sys


def update_wallpaper(mode: str, custom_url: str = "") -> None:
    """Switches desktop wallpaper according to mode."""
    wallpaper_path = "/usr/share/backgrounds/gallos/default.png"
    if mode == "Contest":
        wallpaper_path = "/usr/share/backgrounds/gallos/contest.png"

    if custom_url and os.path.isfile(custom_url):
        wallpaper_path = custom_url

    print(f"[desktop] Updating desktop wallpaper to: {wallpaper_path}")
    try:
        # Terminate previous swaybg instance
        subprocess.run(["pkill", "-x", "swaybg"], check=False)
        # Spawn new swaybg under contestant session
        subprocess.Popen(
            ["su", "-", "contestant", "-c", f"swaybg -i {wallpaper_path} -m fill &"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[desktop] Error updating wallpaper: {e}", file=sys.stderr)


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
        "time_str": f"⏳ {time_str}",
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
