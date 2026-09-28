"""Unit tests for GallosOS Daemon IPC dispatcher."""

import json
from unittest.mock import MagicMock, patch

from daemon.src.main import GallosDaemon


def test_daemon_ipc_start():
    daemon = GallosDaemon()
    daemon.state_machine = MagicMock()
    resp = daemon._process_ipc_command("START 120")
    assert resp == b"OK Contest transition requested\n"
    daemon.state_machine.set_manual_mode.assert_called_once_with("Contest", duration_minutes=120)


def test_daemon_ipc_stop():
    daemon = GallosDaemon()
    daemon.state_machine = MagicMock()
    resp = daemon._process_ipc_command("STOP")
    assert resp == b"OK Default transition requested\n"
    daemon.state_machine.set_manual_mode.assert_called_once_with("Default")


def test_daemon_ipc_status():
    daemon = GallosDaemon()
    daemon.state_machine = MagicMock()
    daemon.state_machine.current_mode = "Contest"
    daemon.state_machine.target_mode = "Contest"
    daemon.state_machine.transition_status = "ready"
    daemon.state_machine.last_error = ""
    daemon.state_machine.evaluate_target_mode.return_value = ("Contest", 3600)
    resp = daemon._process_ipc_command("STATUS")
    data = json.loads(resp.decode("utf-8"))
    assert data["mode"] == "Contest"
    assert data["remaining_seconds"] == 3600
    assert data["target_mode"] == "Contest"
    assert data["transition_status"] == "ready"


def test_daemon_ipc_reload():
    daemon = GallosDaemon()
    daemon.reload_config = MagicMock()
    resp = daemon._process_ipc_command("RELOAD")
    assert resp == b"OK Configuration reloaded\n"
    daemon.reload_config.assert_called_once()


def test_daemon_ipc_reload_reports_failure():
    daemon = GallosDaemon()
    daemon.reload_config = MagicMock(side_effect=ValueError("invalid gallos.toml"))

    resp = daemon._process_ipc_command("RELOAD")

    assert resp.startswith(b"ERROR Configuration reload failed:")
    assert b"invalid gallos.toml" in resp


def test_daemon_ipc_unknown():
    daemon = GallosDaemon()
    resp = daemon._process_ipc_command("FOOBAR")
    assert resp == b"ERROR Unknown command\n"


def test_daemon_ipc_empty():
    daemon = GallosDaemon()
    resp = daemon._process_ipc_command("   ")
    assert resp == b"ERROR Empty command\n"


def test_reload_config_requests_local_root_password_application():
    daemon = GallosDaemon()
    fake_config = {"recovery": {"root_password_hash": "$6$abc$def"}}
    with (
        patch("daemon.src.main.load_active_config", return_value=fake_config),
        patch("daemon.src.main.load_machine_config", return_value={}),
        patch("daemon.src.main.apply_machine_identity"),
        patch("daemon.src.main.apply_local_root_password") as apply_password,
    ):
        daemon.reload_config()
        apply_password.assert_called_once_with()


def test_reload_config_failure_keeps_active_policy():
    daemon = GallosDaemon()
    daemon.config = {"mode": "Contest"}
    daemon.machine_cfg = {"hostname": "seat-old"}
    daemon.state_machine = MagicMock()
    daemon.state_machine.config = daemon.config

    with patch("daemon.src.main.load_active_config", side_effect=ValueError("invalid TOML")):
        try:
            daemon.reload_config()
        except ValueError:
            pass
        else:
            raise AssertionError("reload should reject invalid TOML")

    assert daemon.config == {"mode": "Contest"}
    assert daemon.machine_cfg == {"hostname": "seat-old"}
    assert daemon.state_machine.config == daemon.config
    daemon.state_machine.request_reapply.assert_not_called()
