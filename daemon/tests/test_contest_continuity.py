"""Contest deadlines survive expiry and last-minute policy replacement."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from daemon.src.state_machine import ModeStateMachine


def policy(start=-10, end=50, expired=False):
    now = datetime.now(UTC)
    return {
        "global": {"config_expiration": (now + timedelta(days=-1 if expired else 1)).isoformat()},
        "contest": {
            "schedule": [
                {
                    "start": (now + timedelta(minutes=start)).isoformat(),
                    "end": (now + timedelta(minutes=end)).isoformat(),
                }
            ]
        },
    }


def test_expired_policy_cannot_start_scheduled_contest():
    machine = ModeStateMachine(policy(expired=True), MagicMock())
    assert machine.evaluate_target_mode() == ("Default", 0)


def test_expiration_does_not_interrupt_active_contest():
    config = policy()
    machine = ModeStateMachine(config, MagicMock())
    assert machine.evaluate_target_mode()[0] == "Contest"
    machine.current_mode = "Contest"
    config["global"]["config_expiration"] = "2000-01-01T00:00:00Z"
    assert machine.evaluate_target_mode()[0] == "Contest"


def test_removing_contest_preserves_its_deadline():
    machine = ModeStateMachine(policy(), MagicMock())
    machine.evaluate_target_mode()
    machine.current_mode = "Contest"
    machine.replace_config({"global": {}})
    mode, remaining = machine.evaluate_target_mode()
    assert mode == "Contest"
    assert 2990 <= remaining <= 3000


def test_explicit_new_end_terminates_contest_when_already_past():
    config = policy()
    machine = ModeStateMachine(config, MagicMock())
    machine.evaluate_target_mode()
    machine.current_mode = "Contest"
    replacement = policy(end=-1)
    replacement["contest"]["schedule"][0]["start"] = config["contest"]["schedule"][0]["start"]
    machine.replace_config(replacement)
    assert machine.evaluate_target_mode() == ("Default", 0)


def test_reloaded_duration_keeps_original_monotonic_origin():
    with patch("daemon.src.state_machine.time.monotonic", return_value=100):
        machine = ModeStateMachine(
            {"contest": {"auto_start_on_boot": True, "duration_minutes": 300}}, MagicMock()
        )
        machine.evaluate_target_mode()
    machine.current_mode = "Contest"
    with patch("daemon.src.state_machine.time.monotonic", return_value=7300):
        machine.replace_config({"contest": {"auto_start_on_boot": True, "duration_minutes": 240}})
        assert machine.evaluate_target_mode() == ("Contest", 7200)


def test_manual_expiry_selects_event_without_intermediate_default():
    now = datetime.now(UTC)
    config = {
        "event": {
            "schedule": [
                {
                    "start": (now - timedelta(hours=1)).isoformat(),
                    "end": (now + timedelta(hours=1)).isoformat(),
                }
            ]
        }
    }
    machine = ModeStateMachine(config, MagicMock())
    with patch("daemon.src.state_machine.time.monotonic", return_value=100):
        machine.set_manual_mode("Contest", 1)
    with patch("daemon.src.state_machine.time.monotonic", return_value=161):
        assert machine.evaluate_target_mode() == ("Event", 0)


def test_successful_same_contest_reload_does_not_stop_applications(tmp_path):
    from contextlib import ExitStack

    with ExitStack() as stack:
        stack.enter_context(patch("daemon.src.transition_record.RECORD", tmp_path / "record.json"))
        for name in (
            "unmount_event_data",
            "set_usb_storage_allowed",
            "apply_browser_policy",
            "apply_web_egress",
            "export_waybar_state",
            "update_wallpaper",
        ):
            stack.enter_context(patch(f"daemon.src.state_machine.{name}"))
        stop = stack.enter_context(patch("daemon.src.state_machine.stop_kiosk"))
        release = stack.enter_context(patch("daemon.src.state_machine.release_kiosk"))
        machine = ModeStateMachine(policy(), MagicMock())
        machine.current_mode = "Contest"
        machine.transition_status = "ready"
        machine.replace_config(policy())
        machine.transition_to("Contest", 300)
        assert machine.transition_status == "ready"
        stop.assert_not_called()
        release.assert_not_called()


def test_failed_hot_reload_stops_the_existing_session(tmp_path):
    with (
        patch("daemon.src.transition_record.RECORD", tmp_path / "record.json"),
        patch("daemon.src.state_machine.stop_kiosk") as stop,
        patch("daemon.src.state_machine.start_recovery_console"),
        patch("daemon.src.state_machine.export_waybar_state"),
    ):
        firewall = MagicMock()
        firewall.apply_mode_firewall.side_effect = RuntimeError("policy failed")
        machine = ModeStateMachine(policy(), firewall)
        machine.current_mode = "Contest"
        machine.transition_status = "ready"
        machine.replace_config(policy())
        machine.transition_to("Contest", 300)
        assert machine.transition_status == "error"
        stop.assert_called_once()


def test_expired_active_contest_retains_deadline_across_daemon_restart(tmp_path):
    from daemon.src.transition_record import write_record

    config = policy()
    with patch("daemon.src.transition_record.RECORD", tmp_path / "transition.json"):
        machine = ModeStateMachine(config, MagicMock())
        machine.evaluate_target_mode()
        write_record("Contest", "Contest", "ready", "", clock=machine.clock_snapshot())
        config["global"]["config_expiration"] = "2000-01-01T00:00:00Z"
        restarted = ModeStateMachine(config, MagicMock())
        assert restarted.evaluate_target_mode()[0] == "Contest"


def test_retained_contest_keeps_its_last_fractional_second():
    now = datetime.now(UTC)
    config = policy(expired=True)
    machine = ModeStateMachine(config, MagicMock())
    machine._contest_end = now + timedelta(milliseconds=500)
    with patch("daemon.src.state_machine.datetime") as clock:
        clock.now.return_value = now
        assert machine.evaluate_target_mode() == ("Contest", 1)
