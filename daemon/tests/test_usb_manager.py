"""Unit tests for GallosOS Daemon USB lockdown module."""

from unittest.mock import MagicMock, patch

from daemon.src.usb_manager import (
    set_usb_storage_allowed,
)


def test_set_usb_storage_allowed_true():
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as run:
        set_usb_storage_allowed(True)
    assert run.call_args.args[0] == ["systemctl", "start", "gallos-usb-storage@unlock.service"]


def test_set_usb_storage_allowed_false():
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as run:
        set_usb_storage_allowed(False)
    assert run.call_args.args[0] == ["systemctl", "start", "gallos-usb-storage@lock.service"]
