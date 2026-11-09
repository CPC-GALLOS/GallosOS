"""3-Tier Mode State Machine (Contest > Event > Default) for GallosOS Daemon.

Evaluates scheduled time-windows, monotonic timers, and manual organizer triggers,
orchestrating the Clean State Wipe, dynamic firewall, USB lockdown, and desktop state.
"""

import math
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from typing import Any

from .browser_policy import apply_browser_policy
from .clean_state import reset_contest_scratch
from .config import is_config_expired
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
    reset_contest_scratch()
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
        self._hot_reapply = False
        self._needs_reapply = bool(record and self.transition_status == "ready")
        self._contest_end: datetime | None = None
        self._relative_end: float | None = None
        self._active_window: dict[str, Any] | None = None
        self.manual_override: str | None = None
        self._boot_monotonic = time.monotonic()
        self._manual_start_time: float | None = None
        self._manual_duration_sec: int | None = None
        if record and record.get("clock"):
            self._restore_clock(record["clock"])
        self._persisted_clock = self.clock_snapshot()

    def clock_snapshot(self) -> dict[str, Any]:
        """Persist current-boot deadline origins with the transition journal."""
        return {
            "end": self._contest_end.isoformat() if self._contest_end else None,
            "relative_end": self._relative_end,
            "window": self._active_window,
            "boot_origin": self._boot_monotonic,
            "manual_mode": self.manual_override,
            "manual_origin": self._manual_start_time,
            "manual_duration": self._manual_duration_sec,
        }

    def _restore_clock(self, clock: dict[str, Any]) -> None:
        try:
            self._contest_end = _parse_iso_datetime(clock["end"]) if clock.get("end") else None
            self._relative_end = clock.get("relative_end")
            self._active_window = clock.get("window")
            self._boot_monotonic = clock["boot_origin"]
            self.manual_override = clock.get("manual_mode")
            self._manual_start_time = clock.get("manual_origin")
            self._manual_duration_sec = clock.get("manual_duration")
        except (ValueError, TypeError, KeyError) as exc:
            self.transition_status = "error"
            self.last_error = f"Invalid Contest clock: {exc}"

    def set_manual_mode(self, mode: str | None, duration_minutes: int | None = None) -> None:
        """Allows manual CLI triggers to override state."""
        if self.transition_status == "error":
            self.transition_status = "pending"
            self.last_error = ""
            self._needs_reapply = True
        self._contest_end = None
        self._relative_end = None
        self._active_window = None
        self.manual_override = mode
        if mode == "Contest":
            self._manual_start_time = time.monotonic()
            self._manual_duration_sec = duration_minutes * 60 if duration_minutes else None
        else:
            self._manual_start_time = None
            self._manual_duration_sec = None

    def replace_config(self, config: dict[str, Any]) -> None:
        """Replace policy while retaining an active Contest's original deadline."""
        contest = config.get("contest", {})
        if self._active_window:
            windows = contest.get("schedule", [])
            matches = [w for w in windows if w.get("start") == self._active_window.get("start")]
            if not matches and len(windows) == 1:
                matches = windows
            if matches and "end" in matches[0]:
                self._contest_end = _parse_iso_datetime(matches[0]["end"])
                self._active_window = matches[0].copy()
        if "duration_minutes" in contest and contest["duration_minutes"] != self.config.get(
            "contest", {}
        ).get("duration_minutes"):
            duration = contest["duration_minutes"] * 60
            if self._relative_end is not None:
                self._relative_end = self._boot_monotonic + duration
            if self.manual_override == "Contest" and self._manual_start_time is not None:
                self._manual_duration_sec = duration
        self.config = config
        self._hot_reapply = self.transition_status == "ready"
        self.request_reapply()

    def request_reapply(self) -> None:
        """Reapply a changed config, including when its mode name is unchanged."""
        self._needs_reapply = True
        if self.transition_status == "ready":
            self.transition_status = "pending"

    def _eval_manual_override(self) -> tuple[str, int] | None:
        """Evaluates manual override mode and expiration."""
        if not self.manual_override:
            return None
        rem = 0
        is_manual_contest = (
            self.manual_override == "Contest"
            and self._manual_start_time is not None
            and self._manual_duration_sec
        )
        if is_manual_contest:
            elapsed = int(time.monotonic() - self._manual_start_time)
            rem = max(0, self._manual_duration_sec - elapsed)
            if rem == 0 and self._manual_duration_sec > 0:
                print("[state_machine] Manual contest duration expired. Resuming schedules.")
                self.manual_override = None
                return None
        return self.manual_override, rem

    def _eval_contest_triggers(self, now_utc: datetime) -> tuple[str, int] | None:
        """Checks auto-boot and scheduled triggers for Contest mode."""
        contest_cfg = self.config.get("contest", {})
        if contest_cfg.get("auto_start_on_boot"):
            dur_min = contest_cfg.get("duration_minutes", 300)
            elapsed = int(time.monotonic() - self._boot_monotonic)
            rem = max(0, (dur_min * 60) - elapsed)
            if rem > 0:
                self._relative_end = self._boot_monotonic + dur_min * 60
                return "Contest", rem

        active, rem = _is_schedule_active(contest_cfg.get("schedule", []), now_utc)
        if active:
            for window in contest_cfg.get("schedule", []):
                if _is_window_active(window, now_utc)[0]:
                    self._active_window = window.copy()
                    self._contest_end = _parse_iso_datetime(window["end"])
                    break
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

        now_utc = datetime.now(UTC)

        if self._contest_end is not None:
            remaining = math.ceil((self._contest_end - now_utc).total_seconds())
            if remaining > 0:
                return "Contest", remaining
            self._contest_end = None
            self._active_window = None
        if self._relative_end is not None:
            remaining = math.ceil(self._relative_end - time.monotonic())
            if remaining > 0:
                return "Contest", remaining
            self._relative_end = None
        if is_config_expired(self.config):
            return "Default", 0

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
            "Configured Contest policy applied; session cleanup completed.",
            urgency="critical",
        )

    def _exit_contest_mode(self, target_mode: str) -> None:
        """Restore the target mode's network and USB policy after Contest."""
        print("[state_machine] Post-Contest transition: Applying target mode policy.")
        self.firewall.apply_mode_firewall(target_mode, self.config)
        apply_web_egress(target_mode, self.config)
        usb_allowed = self.config.get(target_mode.lower(), {}).get("allow_usb_storage", True)
        set_usb_storage_allowed(usb_allowed)
        mount_event_data()
        apply_browser_policy(target_mode, self.config)
        update_wallpaper(target_mode)
        send_desktop_notification(
            "Contest Ended",
            (
                "USB mass storage is authorized. You may export your solutions."
                if usb_allowed
                else "USB mass storage remains blocked by organizer policy."
            ),
            urgency="normal",
        )

    def _switch_open_mode(self, target_mode: str) -> None:
        """Transitions between Default and Event modes."""
        self.firewall.apply_mode_firewall(target_mode, self.config)
        apply_web_egress(target_mode, self.config)
        set_usb_storage_allowed(
            self.config.get(target_mode.lower(), {}).get("allow_usb_storage", True)
        )
        mount_event_data()
        apply_browser_policy(target_mode, self.config)
        update_wallpaper(target_mode)

    def transition_to(self, target_mode: str, remaining_sec: int) -> None:
        """Performs state transition actions if mode changed."""
        self.target_mode = target_mode
        if self.transition_status == "error":
            export_waybar_state(self.current_mode, remaining_sec, "error", self.last_error)
            return
        same_mode = target_mode == self.current_mode and not self._needs_reapply
        if same_mode and self.clock_snapshot() == self._persisted_clock:
            export_waybar_state(self.current_mode, remaining_sec, "ready")
            return

        old_mode = self.current_mode
        print(f"[state_machine] MODE TRANSITION: {old_mode} -> {target_mode}")
        hot_reload = self._hot_reapply and old_mode == target_mode
        kiosk_stopped = False
        try:
            if same_mode:
                write_record(target_mode, target_mode, "ready", "", clock=self.clock_snapshot())
                self._persisted_clock = self.clock_snapshot()
                export_waybar_state(target_mode, remaining_sec, "ready")
                return
            if not hot_reload:
                stop_kiosk()
                kiosk_stopped = True
            if old_mode != _BOOT_SENTINEL_MODE:
                write_record(old_mode, target_mode, "pending", "", clock=self.clock_snapshot())
            self._apply_target_mode(target_mode, old_mode)
            self.current_mode = target_mode
            self.transition_status = "ready"
            self.last_error = ""
            write_record(target_mode, target_mode, "ready", "", clock=self.clock_snapshot())
            if not hot_reload:
                kiosk_stopped = False
                release_kiosk()
            self._hot_reapply = False
            self._persisted_clock = self.clock_snapshot()
            self._needs_reapply = False
            export_waybar_state(target_mode, remaining_sec, "ready")
        except Exception as exc:
            self._contain_transition_failure(
                exc, old_mode, target_mode, remaining_sec, kiosk_stopped
            )

    def _contain_transition_failure(
        self,
        exc: Exception,
        old_mode: str,
        target_mode: str,
        remaining_sec: int,
        kiosk_stopped: bool,
    ) -> None:
        """Contain the session independently of recovery services and journal availability."""
        self.transition_status = "error"
        self.last_error = str(exc)
        saved_mode = old_mode if old_mode in ("Contest", "Event", "Default") else "Default"
        self.current_mode = saved_mode
        if not kiosk_stopped:
            try:
                stop_kiosk()
            except Exception as stop_exc:
                self.last_error += f"; session containment failed: {stop_exc}"
        try:
            recovery_hash = self.config.get("recovery", {}).get("root_password_hash")
            start_recovery_console(bool(recovery_hash))
        except Exception as recovery_exc:
            self.last_error += f"; recovery console failed: {recovery_exc}"
        try:
            write_record(
                saved_mode, target_mode, "error", self.last_error, clock=self.clock_snapshot()
            )
        except Exception as journal_exc:
            self.last_error += f"; recovery journal failed: {journal_exc}"
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
            update_wallpaper("Contest")
        elif old_mode == "Contest":
            self._exit_contest_mode(target_mode)
        else:
            self._switch_open_mode(target_mode)
