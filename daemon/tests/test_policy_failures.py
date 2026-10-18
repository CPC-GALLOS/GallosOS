"""Required lockdown writers must report failures to the transition gate."""

from unittest.mock import patch

import pytest

from daemon.src.browser_policy import apply_browser_policy
from daemon.src.usb_storage_host import apply_usb_policy


def test_browser_policy_write_error_propagates():
    with patch("daemon.src.browser_policy._write_policy_json", side_effect=OSError("read-only")):
        with pytest.raises(OSError, match="read-only"):
            apply_browser_policy("Contest", {})


def test_udev_reload_failure_propagates(tmp_path):
    import subprocess

    with (
        patch("daemon.src.usb_storage_host.POLKIT_RULE_FILE", tmp_path / "polkit.rules"),
        patch("daemon.src.usb_storage_host.UDEV_RULE_FILE", tmp_path / "udev.rules"),
        patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "udevadm")),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            apply_usb_policy(False)
