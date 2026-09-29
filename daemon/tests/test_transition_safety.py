"""Failures must not be reported as a completed Contest transition."""

from unittest.mock import MagicMock, patch

import pytest

from daemon.src.firewall import FirewallManager
from daemon.src.state_machine import ModeStateMachine


def test_firewall_failure_does_not_commit_mode():
    manager = FirewallManager()
    with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="bad rules")):
        with pytest.raises(RuntimeError, match="bad rules"):
            manager.apply_mode_firewall("Contest", {})
    assert manager._current_mode == "Default"


def test_failed_contest_policy_does_not_publish_contest(tmp_path):
    firewall = MagicMock()
    firewall.apply_mode_firewall.side_effect = RuntimeError("nft failed")
    machine = ModeStateMachine({"mode": "Default"}, firewall)
    with (
        patch("daemon.src.state_machine.perform_clean_state_wipe"),
        patch("daemon.src.state_machine.unmount_event_data"),
        patch("daemon.src.state_machine.export_waybar_state") as publish,
        patch("daemon.src.state_machine.stop_kiosk"),
        patch("daemon.src.state_machine.start_recovery_console"),
        patch("daemon.src.transition_record.RECORD", tmp_path / "transition.json"),
    ):
        machine.transition_to("Contest", 120)
    assert machine.current_mode != "Contest"
    assert machine.transition_status == "error"
    assert "nft failed" in machine.last_error
    assert publish.call_args.args[0] != "Contest"


def test_failed_training_proxy_keeps_kiosk_stopped(tmp_path):
    machine = ModeStateMachine({"default": {"allowed_websites": ["codeforces.com"]}}, MagicMock())
    with (
        patch("daemon.src.state_machine.stop_kiosk"),
        patch("daemon.src.state_machine.release_kiosk") as release,
        patch(
            "daemon.src.state_machine.apply_web_egress", side_effect=RuntimeError("proxy failed")
        ),
        patch("daemon.src.state_machine.start_recovery_console"),
        patch("daemon.src.state_machine.export_waybar_state"),
        patch("daemon.src.transition_record.RECORD", tmp_path / "transition.json"),
    ):
        machine.transition_to("Default", 0)
    assert machine.transition_status == "error"
    release.assert_not_called()


def test_failed_transition_latches_until_organizer_retries(tmp_path):
    firewall = MagicMock()
    firewall.apply_mode_firewall.side_effect = RuntimeError("nft failed")
    machine = ModeStateMachine({"recovery": {"root_password_hash": "hash"}}, firewall)
    with (
        patch("daemon.src.state_machine.stop_kiosk"),
        patch("daemon.src.state_machine.start_recovery_console"),
        patch("daemon.src.state_machine.export_waybar_state"),
        patch("daemon.src.transition_record.RECORD", tmp_path / "transition.json"),
    ):
        machine.transition_to("Contest", 120)
        machine.transition_to("Contest", 119)
    assert firewall.apply_mode_firewall.call_count == 1
    machine.set_manual_mode("Contest", duration_minutes=10)
    assert machine.transition_status != "error"


def test_restart_in_contest_reapplies_policy_without_wiping(tmp_path):
    from daemon.src.transition_record import write_record

    with patch("daemon.src.transition_record.RECORD", tmp_path / "transition.json"):
        write_record("Contest", "Contest", "ready", "")
        firewall = MagicMock()
        machine = ModeStateMachine({"mode": "Contest"}, firewall)
        with (
            patch("daemon.src.state_machine.stop_kiosk"),
            patch("daemon.src.state_machine.release_kiosk"),
            patch("daemon.src.state_machine.unmount_event_data"),
            patch("daemon.src.state_machine.set_usb_storage_allowed"),
            patch("daemon.src.state_machine.apply_browser_policy"),
            patch("daemon.src.state_machine.apply_web_egress") as web_egress,
            patch("daemon.src.state_machine.perform_clean_state_wipe") as wipe,
            patch("daemon.src.state_machine.export_waybar_state"),
        ):
            machine.transition_to("Contest", 20)
    assert machine.transition_status == "ready"
    assert firewall.apply_mode_firewall.call_count == 1
    web_egress.assert_called_once_with("Contest", machine.config)
    wipe.assert_not_called()


def test_retrying_same_mode_after_error_reapplies_policy(tmp_path):
    machine = ModeStateMachine({"mode": "Default"}, MagicMock())
    machine.current_mode = "Default"
    machine.transition_status = "error"
    machine._needs_reapply = False
    machine.set_manual_mode("Default")
    with (
        patch("daemon.src.state_machine.stop_kiosk"),
        patch("daemon.src.state_machine.release_kiosk") as release,
        patch("daemon.src.state_machine.mount_event_data") as mount,
        patch("daemon.src.state_machine.set_usb_storage_allowed"),
        patch("daemon.src.state_machine.apply_browser_policy"),
        patch("daemon.src.state_machine.apply_web_egress"),
        patch("daemon.src.state_machine.update_wallpaper"),
        patch("daemon.src.state_machine.export_waybar_state"),
        patch("daemon.src.transition_record.RECORD", tmp_path / "transition.json"),
    ):
        machine.transition_to("Default", 0)
    mount.assert_called_once()
    release.assert_called_once()
    assert machine.transition_status == "ready"
