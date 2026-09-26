"""The contestant session is released only after policy application."""

from unittest.mock import MagicMock, patch

import pytest

from daemon.src.session_gate import release_kiosk, stop_kiosk


def test_failed_stop_cannot_leave_kiosk_running():
    failed = MagicMock(returncode=1, stderr="unit failed")
    killed = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", side_effect=[failed, killed]) as run:
        with pytest.raises(RuntimeError, match="unit failed"):
            stop_kiosk()
    assert run.call_args_list[1].args[0] == ["pkill", "-KILL", "-u", "contestant"]


def test_failed_getty_start_does_not_mark_kiosk_ready(tmp_path):
    failed = MagicMock(returncode=1, stderr="start failed")
    with (
        patch("subprocess.run", return_value=failed),
        patch("daemon.src.session_gate.READY_MARKER", tmp_path / "ready"),
    ):
        with pytest.raises(RuntimeError, match="start failed"):
            release_kiosk()
    assert not (tmp_path / "ready").exists()
