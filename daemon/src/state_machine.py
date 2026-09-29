"""3-Tier Mode State Machine (Contest > Event > Default) for GallosOS Daemon.

Evaluates scheduled time-windows, monotonic timers, and manual organizer triggers,
orchestrating the Clean State Wipe, dynamic firewall, USB lockdown, and desktop state.
"""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

from .browser_policy import apply_browser_policy
from .desktop import export_waybar_state, send_desktop_notification, update_wallpaper
from .firewall import FirewallManager
from .session_gate import release_kiosk, start_recovery_console, stop_kiosk
from .storage import mount_event_data, unmount_event_data
from .transition_record import read_record, write_record
from .usb_manager import set_usb_storage_allowed
from .web_egress import apply_web_egress

UTC_TZ_OFFSET = "+00:00"

# Not a real mode: ModeStateMachine starts here so the first transition_to()
# call always runs a real transition (_enter_contest_mode/_exit_contest_mode/
# _switch_open_mode), even when the target is "Default" — otherwise
# target_mode == current_mode short-circuits transition_to() on a boot
# straight into Default, and mount_event_data() (called from
# _switch_open_mode) would never run on the common case of a normal boot.
_BOOT_SENTINEL_MODE = "__gallos_boot__"


def _parse_iso_datetime(dt_str: str) -> datetime:
    """Parses an ISO 8601 string, normalizing UTC 'Z' indicator to '+00:00'."""
    normalized = dt_str.replace("Z", UTC_TZ_OFFSET)
    return datetime.fromisoformat(normalized)


def _wipe_directory_contents(dir_path: str) -> None:
    """Removes all files, symlinks, and subdirectories within dir_path."""
    if not os.path.isdir(dir_path):
        return
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        try:
            if os.path.isdir(item_path) and not os.path.islink(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        except Exception as e:
            raise RuntimeError(f"Could not wipe {item_path}: {e}") from e


def _populate_from_skel(skel_dir: str, target_dir: str) -> None:
    """Restores default files and directories from skeleton template."""
    if not os.path.isdir(skel_dir):
        raise RuntimeError(f"Missing contestant skeleton: {skel_dir}")
    for item in os.listdir(skel_dir):
        src = os.path.join(skel_dir, item)
        dst = os.path.join(target_dir, item)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, symlinks=True)
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            raise RuntimeError(f"Could not restore {src}: {e}") from e


def perform_clean_state_wipe() -> None:
    """Executes the Clean State Wipe on Contest entry."""
    print("[state_machine] Performing destructive Clean State Wipe of /home/contestant/...")
    home_dir = "/home/contestant"
    skel_dir = "/etc/skel"
    _wipe_directory_contents(home_dir)
    _populate_from_skel(skel_dir, home_dir)
    subprocess.run(["chown", "-R", "contestant:contestant", home_dir], check=True, timeout=30)
    print("[state_machine] Clean State Wipe completed successfully.")


def _is_window_active(window: dict[str, Any], now_utc: datetime) -> tuple[bool, int]:
    """Evaluates whether a single ISO 8601 start/end time_window is currently active."""
    start_str = window.get("start")
    end_str = window.get("end")
    if not (start_str and end_str):
        return False, 0
    try:
        start_dt = _parse_iso_datetime(start_str)
        end_dt = _parse_iso_datetime(end_str)
        if start_dt <= now_utc < end_dt:
            rem = int((end_dt - now_utc).total_seconds())
            return True, rem
    except Exception as e:
        print(f"[state_machine] Schedule parsing error: {e}", file=sys.stderr)
    return False, 0


def _is_schedule_active(schedule: list[dict[str, Any]], now_utc: datetime) -> tuple[bool, int]:
    """Evaluates a `schedule` array (schema: time_window[]) of one or more windows,
    returning the first one currently active, if any."""
    for window in schedule:
        active, rem = _is_window_active(window, now_utc)
        if active:
            return True, rem
    return False, 0


class ModeStateMachine:
    """Orchestrates system mode state and transitions."""

    def __init__(self, config: dict[str, Any], firewall: FirewallManager) -> None:
        self.config = config
        self.firewall = firewall
        record = read_record()
        self.current_mode: str = record["mode"] if record else _BOOT_SENTINEL_MODE
        self.target_mode: str = record["target_mode"] if record else "Unknown"
        self.transition_status: str = record["transition_status"] if record else "pending"
        self.last_error: str = record["last_error"] if record else ""
        self._needs_reapply = bool(record and self.transition_status == "ready")
        self.manual_override: str | None = None
        self._boot_monotonic = time.monotonic()
        self._manual_start_time: float | None = None
        self._manual_duration_sec: int | None = None

    def set_manual_mode(self, mode: str | None, duration_minutes: int | None = None) -> None:
        """Allows manual CLI triggers to override state."""
        if self.transition_status == "error":
            self.transition_status = "pending"
            self.last_error = ""
            self._needs_reapply = True
        self.manual_override = mode
        if mode == "Contest":
            self._manual_start_time = time.monotonic()
            self._manual_duration_sec = duration_minutes * 60 if duration_minutes else None
        else:
            self._manual_start_time = None
            self._manual_duration_sec = None

    def request_reapply(self) -> None:
        """Reapply a changed config, including when its mode name is unchanged."""
        self._needs_reapply = True

    def _eval_manual_override(self) -> tuple[str, int] | None:
        """Evaluates manual override mode and expiration."""
        if not self.manual_override:
            return None
        rem = 0
        is_manual_contest = (
            self.manual_override == "Contest"
            and self._manual_start_time
            and self._manual_duration_sec
        )
        if is_manual_contest:
            elapsed = int(time.monotonic() - self._manual_start_time)
            rem = max(0, self._manual_duration_sec - elapsed)
            if rem == 0 and self._manual_duration_sec > 0:
                print("[state_machine] Manual contest duration expired. Reverting to Default.")
                self.manual_override = None
                return "Default", 0
        return self.manual_override, rem

    def _eval_contest_triggers(self, now_utc: datetime) -> tuple[str, int] | None:
        """Checks auto-boot and scheduled triggers for Contest mode."""
        contest_cfg = self.config.get("contest", {})
        if contest_cfg.get("auto_start_on_boot"):
            dur_min = contest_cfg.get("duration_minutes", 300)
            elapsed = int(time.monotonic() - self._boot_monotonic)
            rem = max(0, (dur_min * 60) - elapsed)
            if rem > 0:
                return "Contest", rem

        active, rem = _is_schedule_active(contest_cfg.get("schedule", []), now_utc)
        if active:
            return "Contest", rem
        return None

    def _eval_event_triggers(self, now_utc: datetime) -> tuple[str, int] | None:
        """Checks scheduled triggers for Event mode."""
        event_cfg = self.config.get("event", {})
        active, _ = _is_schedule_active(event_cfg.get("schedule", []), now_utc)
        if active:
            return "Event", 0
        return None

    def evaluate_target_mode(self) -> tuple[str, int]:
        """Calculates the current target mode and remaining contest seconds."""
        if (manual_res := self._eval_manual_override()) is not None:
            return manual_res

        now_utc = datetime.now(timezone.utc)

        if (contest_res := self._eval_contest_triggers(now_utc)) is not None:
            return contest_res

        if (event_res := self._eval_event_triggers(now_utc)) is not None:
            return event_res

        return self.config.get("mode", "Default"), 0

    def _enter_contest_mode(self) -> None:
        """Applies all security and system lockdowns for Contest entry."""
        self.firewall.apply_mode_firewall("Contest", self.config)
        apply_web_egress("Contest", self.config)
        unmount_event_data()
        set_usb_storage_allowed(False)
        apply_browser_policy("Contest", self.config)
        perform_clean_state_wipe()
        update_wallpaper("Contest")
        send_desktop_notification(
            "Contest Mode Activated",
            "Strict Zero-Trust security engaged. USB locked.",
            urgency="critical",
        )

    def _exit_contest_mode(self, target_mode: str) -> None:
        """Restores network and unlocks USB storage when leaving Contest mode."""
        print(
            "[state_machine] Post-Contest transition: Unlocking USB storage and restoring network."
        )
        self.firewall.apply_mode_firewall(target_mode, self.config)
        apply_web_egress(target_mode, self.config)
        set_usb_storage_allowed(True)
        mount_event_data()
        apply_browser_policy(target_mode, self.config)
        update_wallpaper(target_mode)
        send_desktop_notification(
            "Contest Ended",
            "USB mass storage is now authorized. You may export your solutions.",
            urgency="normal",
        )

    def _switch_open_mode(self, target_mode: str) -> None:
        """Transitions between Default and Event modes."""
        self.firewall.apply_mode_firewall(target_mode, self.config)
        apply_web_egress(target_mode, self.config)
        set_usb_storage_allowed(True)
        mount_event_data()
        apply_browser_policy(target_mode, self.config)
        update_wallpaper(target_mode)

    def transition_to(self, target_mode: str, remaining_sec: int) -> None:
        """Performs state transition actions if mode changed."""
        self.target_mode = target_mode
        if self.transition_status == "error":
            export_waybar_state(self.current_mode, remaining_sec, "error", self.last_error)
            return
        if target_mode == self.current_mode and not self._needs_reapply:
            export_waybar_state(self.current_mode, remaining_sec, "ready")
            return

        old_mode = self.current_mode
        print(f"[state_machine] MODE TRANSITION: {old_mode} -> {target_mode}")
        try:
            stop_kiosk()
            if old_mode != _BOOT_SENTINEL_MODE:
                write_record(old_mode, target_mode, "pending", "")
            self._apply_target_mode(target_mode, old_mode)
            self.current_mode = target_mode
            self.transition_status = "ready"
            self.last_error = ""
            write_record(target_mode, target_mode, "ready", "")
            release_kiosk()
            self._needs_reapply = False
            export_waybar_state(target_mode, remaining_sec, "ready")
        except Exception as exc:
            self.transition_status = "error"
            self.last_error = str(exc)
            saved_mode = old_mode if old_mode in ("Contest", "Event", "Default") else "Default"
            self.current_mode = saved_mode
            write_record(saved_mode, target_mode, "error", self.last_error)
            try:
                recovery_hash = self.config.get("recovery", {}).get("root_password_hash")
                start_recovery_console(bool(recovery_hash))
            except Exception as recovery_exc:
                self.last_error += f"; recovery console failed: {recovery_exc}"
                write_record(saved_mode, target_mode, "error", self.last_error)
            print(f"[state_machine] Transition failed: {self.last_error}", file=sys.stderr)
            export_waybar_state(saved_mode, remaining_sec, "error", self.last_error)

    def _apply_target_mode(self, target_mode: str, old_mode: str) -> None:
        if target_mode == "Contest" and old_mode != "Contest":
            self._enter_contest_mode()
        elif target_mode == "Contest":
            self.firewall.apply_mode_firewall("Contest", self.config)
            apply_web_egress("Contest", self.config)
            unmount_event_data()
            set_usb_storage_allowed(False)
            apply_browser_policy("Contest", self.config)
        elif old_mode == "Contest":
            self._exit_contest_mode(target_mode)
        else:
            self._switch_open_mode(target_mode)
