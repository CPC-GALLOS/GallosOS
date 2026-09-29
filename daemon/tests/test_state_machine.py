"""Unit tests for gallosd 3-tier mode state machine."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from daemon.src.state_machine import ModeStateMachine


def test_state_machine_default_fallback():
    mock_firewall = MagicMock()
    config = {"mode": "Default"}
    sm = ModeStateMachine(config, mock_firewall)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Default"
    assert rem == 0


def test_state_machine_manual_override():
    mock_firewall = MagicMock()
    config = {"mode": "Default"}
    sm = ModeStateMachine(config, mock_firewall)
    sm.set_manual_mode("Contest", duration_minutes=60)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Contest"
    assert 3500 <= rem <= 3600

    sm.set_manual_mode("Default")
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Default"
    assert rem == 0


def test_state_machine_auto_start_on_boot():
    mock_firewall = MagicMock()
    config = {"mode": "Default", "contest": {"auto_start_on_boot": True, "duration_minutes": 10}}
    sm = ModeStateMachine(config, mock_firewall)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Contest"
    assert 590 <= rem <= 600


def test_first_transition_to_default_mounts_event_data(tmp_path):
    """A boot straight into Default mode must still run _switch_open_mode()
    (and thus mount_event_data()) — current_mode must not start equal to
    the first evaluated target, or transition_to() short-circuits."""
    mock_firewall = MagicMock()
    sm = ModeStateMachine({"mode": "Default"}, mock_firewall)
    with (
        patch("daemon.src.state_machine.mount_event_data") as mock_mount,
        patch("daemon.src.state_machine.set_usb_storage_allowed"),
        patch("daemon.src.state_machine.apply_browser_policy"),
        patch("daemon.src.state_machine.apply_web_egress"),
        patch("daemon.src.state_machine.update_wallpaper"),
        patch("daemon.src.state_machine.export_waybar_state"),
        patch("daemon.src.state_machine.stop_kiosk"),
        patch("daemon.src.state_machine.release_kiosk"),
        patch("daemon.src.transition_record.RECORD", tmp_path / "transition.json"),
    ):
        sm.transition_to("Default", 0)
        mock_mount.assert_called_once()
    assert sm.current_mode == "Default"


def test_state_machine_wall_clock_schedule():
    """schema: contest.schedule is an array of {start, end} time_window objects
    (schema/directives.schema.json's time_window def), not a single dict, and
    not start_time/end_time — matches examples/*.toml's [[contest.schedule]]."""
    mock_firewall = MagicMock()
    now_utc = datetime.now(timezone.utc)
    start_utc = now_utc - timedelta(minutes=10)
    end_utc = now_utc + timedelta(minutes=50)

    config = {
        "mode": "Default",
        "contest": {"schedule": [{"start": start_utc.isoformat(), "end": end_utc.isoformat()}]},
    }
    sm = ModeStateMachine(config, mock_firewall)
    mode, rem = sm.evaluate_target_mode()
    assert mode == "Contest"
    assert 2900 <= rem <= 3000


def test_state_machine_schedule_with_multiple_windows_checks_all():
    """A schedule array with several windows must find whichever one is
    currently active, not just the first entry."""
    mock_firewall = MagicMock()
    now_utc = datetime.now(timezone.utc)
    past_start = now_utc - timedelta(hours=2)
    past_end = now_utc - timedelta(hours=1)
    active_start = now_utc - timedelta(minutes=5)
    active_end = now_utc + timedelta(minutes=5)

    config = {
        "mode": "Default",
        "event": {
            "schedule": [
                {"start": past_start.isoformat(), "end": past_end.isoformat()},
                {"start": active_start.isoformat(), "end": active_end.isoformat()},
            ]
        },
    }
    sm = ModeStateMachine(config, mock_firewall)
    mode, _ = sm.evaluate_target_mode()
    assert mode == "Event"
