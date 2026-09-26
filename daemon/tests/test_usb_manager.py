"""Unit tests for GallosOS Daemon USB lockdown module."""

from unittest.mock import MagicMock, patch

from daemon.src.usb_manager import (
    set_usb_storage_allowed,
)


def test_set_usb_storage_allowed_true():
    with patch("os.path.exists", return_value=True):
        with patch("os.remove") as mock_remove:
            with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
                set_usb_storage_allowed(True)
                assert mock_remove.call_count == 2
                expected_cmd = ["udevadm", "control", "--reload-rules"]
                assert mock_run.call_args.args[0] == expected_cmd


def test_set_usb_storage_allowed_false():
    with patch("daemon.src.usb_manager._write_rule_file") as mock_write:
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            set_usb_storage_allowed(False)
            assert mock_write.call_count == 2
            expected_cmd = ["udevadm", "control", "--reload-rules"]
            assert mock_run.call_args.args[0] == expected_cmd
