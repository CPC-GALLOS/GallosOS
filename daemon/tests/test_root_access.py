"""Unit tests for GallosOS Daemon root recovery access module."""

import subprocess
from unittest.mock import patch

import pytest

from daemon.src.root_access import apply_local_root_password, set_root_password


def test_set_root_password_applies_hash():
    with patch("subprocess.run") as mock_run:
        set_root_password("$6$abc$def")
        mock_run.assert_called_once_with(
            ["chpasswd", "-e"], input="root:$6$abc$def\n", text=True, check=True
        )


def test_set_root_password_none_locks_root():
    with patch("subprocess.run") as mock_run:
        set_root_password(None)
        mock_run.assert_called_once_with(["passwd", "-l", "root"], check=True)


def test_set_root_password_empty_string_locks_root():
    with patch("subprocess.run") as mock_run:
        set_root_password("")
        mock_run.assert_called_once_with(["passwd", "-l", "root"], check=True)


def test_set_root_password_rejects_chpasswd_failure():
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["chpasswd", "-e"])):
        with pytest.raises(subprocess.CalledProcessError):
            set_root_password("$6$malformed")


def test_apply_local_root_password_reports_service_failure():
    from unittest.mock import MagicMock

    with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="lock denied")):
        with pytest.raises(RuntimeError, match="lock denied"):
            apply_local_root_password()
