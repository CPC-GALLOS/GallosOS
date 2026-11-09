"""Regression coverage for runtime contract findings F01 through F06."""

from unittest.mock import MagicMock, patch

import pytest

from daemon.src import state_machine
from daemon.src.state_machine import ModeStateMachine


@pytest.fixture
def machine(tmp_path):
    with patch("daemon.src.transition_record.RECORD", tmp_path / "record.json"):
        yield ModeStateMachine({"contest": {"duration_minutes": 300}}, MagicMock())


@pytest.mark.parametrize("replacement,expected", [(300, 3540), (120, 7140), (None, 3540)])
def test_manual_deadline_changes_only_with_policy_duration(machine, replacement, expected):
    with patch("daemon.src.state_machine.time.monotonic", return_value=100):
        machine.set_manual_mode("Contest", 60)
    config = {"contest": {} if replacement is None else {"duration_minutes": replacement}}
    with patch("daemon.src.state_machine.time.monotonic", return_value=160):
        machine.replace_config(config)
        assert machine.evaluate_target_mode() == ("Contest", expected)


@pytest.mark.parametrize("mode", ["Default", "Contest"])
def test_same_mode_manual_command_survives_restart_without_session_restart(machine, mode):
    machine.current_mode = mode
    machine.transition_status = "ready"
    with (
        patch.object(state_machine, "stop_kiosk") as stop,
        patch.object(state_machine, "release_kiosk") as release,
        patch.object(state_machine, "export_waybar_state"),
        patch.object(machine, "_apply_target_mode") as apply,
        patch("daemon.src.state_machine.time.monotonic", return_value=100),
    ):
        machine.set_manual_mode(mode, 60)
        machine.transition_to(*machine.evaluate_target_mode())
        restarted = ModeStateMachine(machine.config, MagicMock())
        assert restarted.manual_override == mode
        assert restarted.evaluate_target_mode() == (mode, 3600 if mode == "Contest" else 0)
        stop.assert_not_called()
        release.assert_not_called()
        apply.assert_not_called()


@pytest.mark.parametrize("failure_at", ["pending", "ready", "policy"])
def test_hot_reload_journal_failures_cannot_skip_containment(machine, failure_at):
    machine.current_mode = "Contest"
    machine.transition_status = "ready"
    machine.replace_config(machine.config.copy())
    calls = []

    def journal(_mode, _target, status, _error, **_kwargs):
        calls.append(status)
        if status == failure_at or status == "error":
            raise OSError("journal unavailable")

    with (
        patch.object(state_machine, "write_record", side_effect=journal),
        patch.object(state_machine, "stop_kiosk") as stop,
        patch.object(state_machine, "release_kiosk") as release,
        patch.object(state_machine, "start_recovery_console") as recovery,
        patch.object(state_machine, "export_waybar_state") as publish,
        patch.object(machine, "_apply_target_mode") as apply,
    ):
        if failure_at == "policy":
            apply.side_effect = RuntimeError("policy failed")
        machine.transition_to("Contest", 60)
        stop.assert_called_once()
        recovery.assert_called_once()
        release.assert_not_called()
        assert machine.transition_status == "error"
        assert "journal unavailable" in machine.last_error
        assert publish.call_args.args[2] == "error"


def test_shortened_manual_policy_duration_uses_elapsed_original_origin(machine):
    with patch("daemon.src.state_machine.time.monotonic", return_value=100):
        machine.set_manual_mode("Contest", 60)
    with patch("daemon.src.state_machine.time.monotonic", return_value=221):
        machine.replace_config({"contest": {"duration_minutes": 2}})
        assert machine.evaluate_target_mode() == ("Default", 0)


def test_same_mode_clock_is_written_once_and_write_failure_stops_session(machine):
    machine.current_mode = "Default"
    machine.transition_status = "ready"
    with (
        patch.object(state_machine, "write_record") as journal,
        patch.object(state_machine, "stop_kiosk") as stop,
        patch.object(state_machine, "start_recovery_console") as recovery,
        patch.object(state_machine, "export_waybar_state"),
    ):
        machine.set_manual_mode("Default")
        machine.transition_to("Default", 0)
        machine.transition_to("Default", 0)
        journal.assert_called_once()
        stop.assert_not_called()
        journal.side_effect = OSError("read-only journal")
        machine.set_manual_mode(None)
        machine.transition_to("Default", 0)
        stop.assert_called_once()
        recovery.assert_called_once()
        assert machine.transition_status == "error"
        assert "read-only journal" in machine.last_error


def test_containment_and_recovery_failures_are_reported_even_without_journal(machine):
    machine.current_mode = "Contest"
    machine.transition_status = "ready"
    machine.replace_config(machine.config.copy())
    with (
        patch.object(state_machine, "write_record", side_effect=OSError("no journal")),
        patch.object(state_machine, "stop_kiosk", side_effect=RuntimeError("stop failed")),
        patch.object(
            state_machine, "start_recovery_console", side_effect=RuntimeError("no tty")
        ) as recovery,
        patch.object(state_machine, "export_waybar_state") as publish,
    ):
        machine.transition_to("Contest", 60)
        recovery.assert_called_once()
        assert all(error in machine.last_error for error in ("no journal", "stop failed", "no tty"))
        assert publish.call_args.args[3] == machine.last_error


def test_manual_expiry_into_scheduled_contest_persists_new_deadline(machine):
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    machine.config = {
        "contest": {
            "schedule": [
                {
                    "start": (now - timedelta(minutes=5)).isoformat(),
                    "end": (now + timedelta(minutes=30)).isoformat(),
                }
            ]
        }
    }
    machine.current_mode = "Contest"
    machine.transition_status = "ready"
    with (
        patch.object(state_machine, "export_waybar_state"),
        patch.object(state_machine, "stop_kiosk") as stop,
        patch.object(state_machine, "release_kiosk") as release,
        patch("daemon.src.state_machine.time.monotonic", return_value=100),
    ):
        machine.set_manual_mode("Contest", 1)
        machine.transition_to(*machine.evaluate_target_mode())
    with (
        patch.object(state_machine, "export_waybar_state"),
        patch.object(state_machine, "stop_kiosk", stop),
        patch.object(state_machine, "release_kiosk", release),
        patch("daemon.src.state_machine.time.monotonic", return_value=161),
    ):
        machine.transition_to(*machine.evaluate_target_mode())
        restarted = ModeStateMachine(
            {"global": {"config_expiration": "2000-01-01T00:00:00Z"}}, MagicMock()
        )
        assert restarted.manual_override is None
        mode, remaining = restarted.evaluate_target_mode()
        assert mode == "Contest"
        assert 1790 <= remaining <= 1800
        stop.assert_not_called()
        release.assert_not_called()


def test_failed_release_retries_containment(machine):
    with (
        patch.object(state_machine, "export_waybar_state"),
        patch.object(state_machine, "stop_kiosk") as stop,
        patch.object(state_machine, "start_recovery_console"),
        patch.object(state_machine, "release_kiosk", side_effect=RuntimeError("partial restart")),
        patch.object(machine, "_apply_target_mode"),
    ):
        machine.transition_to("Default", 0)
        assert stop.call_count == 2
        assert machine.transition_status == "error"
