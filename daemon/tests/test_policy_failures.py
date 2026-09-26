"""Required lockdown writers must report failures to the transition gate."""

from unittest.mock import MagicMock, patch

import pytest

from daemon.src.browser_policy import apply_browser_policy
from daemon.src.usb_manager import set_usb_storage_allowed


def test_browser_policy_write_error_propagates():
    with patch("daemon.src.browser_policy._write_policy_json", side_effect=OSError("read-only")):
        with pytest.raises(OSError, match="read-only"):
            apply_browser_policy("Contest", {})


def test_udev_reload_failure_propagates():
    with (
        patch("os.makedirs"),
        patch("daemon.src.usb_manager._write_rule_file"),
        patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="udev failed")),
    ):
        with pytest.raises(RuntimeError, match="udev failed"):
            set_usb_storage_allowed(False)
