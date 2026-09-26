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
