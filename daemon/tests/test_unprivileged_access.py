"""Unit tests for unprivileged access, peer credential authorization, and diagnostics."""

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock

from daemon.src.main import GallosDaemon


def _load_gallos_ctl():
    p = Path(__file__).resolve().parents[2] / "daemon" / "gallosctl"
    loader = SourceFileLoader("gallos_ctl", str(p))
    spec = importlib.util.spec_from_file_location("gallos_ctl", str(p), loader=loader)
    assert spec is not None
    ctl = importlib.util.module_from_spec(spec)
    loader.exec_module(ctl)
    return ctl


def test_ipc_mutating_commands_rejected_for_non_root():
    daemon = GallosDaemon()
    daemon.state_machine = MagicMock()

    # UID 1000 (contestant) attempting mutating commands
    resp_start = daemon._process_ipc_command("START 120", client_uid=1000)
    assert resp_start == b"ERROR Permission denied: root required\n"
    daemon.state_machine.set_manual_mode.assert_not_called()

    resp_stop = daemon._process_ipc_command("STOP", client_uid=1000)
    assert resp_stop == b"ERROR Permission denied: root required\n"
    daemon.state_machine.set_manual_mode.assert_not_called()

    resp_reload = daemon._process_ipc_command("RELOAD", client_uid=1000)
    assert resp_reload == b"ERROR Permission denied: root required\n"


def test_ipc_mutating_commands_allowed_for_root():
    daemon = GallosDaemon()
    daemon.state_machine = MagicMock()

    # UID 0 (root) attempting mutating commands
    resp_start = daemon._process_ipc_command("START 120", client_uid=0)
    assert resp_start == b"OK Contest transition requested\n"
    daemon.state_machine.set_manual_mode.assert_called_once_with("Contest", duration_minutes=120)

    daemon.state_machine.reset_mock()
    resp_stop = daemon._process_ipc_command("STOP", client_uid=0)
    assert resp_stop == b"OK Default transition requested\n"
    daemon.state_machine.set_manual_mode.assert_called_once_with("Default")


def test_ipc_status_allowed_for_non_root():
    daemon = GallosDaemon()
    daemon.state_machine = MagicMock()
    daemon.state_machine.current_mode = "Default"
    daemon.state_machine.target_mode = "Default"
    daemon.state_machine.transition_status = "ready"
    daemon.state_machine.last_error = ""
    daemon.state_machine.evaluate_target_mode.return_value = ("Default", 0)

    # UID 1000 (contestant) requesting status
    resp = daemon._process_ipc_command("STATUS", client_uid=1000)
    data = json.loads(resp.decode("utf-8"))
    assert data["mode"] == "Default"
    assert data["transition_status"] == "ready"


def test_gallos_ctl_offline_status_fallback(tmp_path, monkeypatch, capsys):
    ctl = _load_gallos_ctl()

    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps({"mode": "Contest", "remaining_sec": 300, "transition_status": "ready"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(ctl, "SOCKET_PATH", str(tmp_path / "nonexistent.sock"))
    monkeypatch.setattr(ctl, "STATE_FILE", str(state_file))

    ctl.send_command("STATUS")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["mode"] == "Contest"
    assert data["remaining_sec"] == 300


def test_gallos_ctl_check_command(capsys):
    ctl = _load_gallos_ctl()

    ctl.run_check(as_json=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "daemon" in data
    assert "wayland" in data
    assert "session" in data
    assert "network" in data
