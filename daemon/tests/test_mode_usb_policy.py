"""Validated per-mode USB policy must survive every transition path."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from daemon.src.state_machine import ModeStateMachine


@pytest.mark.parametrize("old_mode", ["__gallos_boot__", "Default", "Event", "Contest"])
@pytest.mark.parametrize("target_mode", ["Default", "Event"])
@pytest.mark.parametrize("setting", [False, True, None])
def test_usb_policy_is_honored_on_entry_exit_and_reapply(tmp_path, old_mode, target_mode, setting):
    target_config = {} if setting is None else {"allow_usb_storage": setting}
    config = {target_mode.lower(): target_config}
    with ExitStack() as stack:
        stack.enter_context(patch("daemon.src.transition_record.RECORD", tmp_path / "record.json"))
        for name in (
            "stop_kiosk",
            "release_kiosk",
            "mount_event_data",
            "apply_web_egress",
            "apply_browser_policy",
            "update_wallpaper",
            "send_desktop_notification",
            "export_waybar_state",
        ):
            stack.enter_context(patch(f"daemon.src.state_machine.{name}"))
        usb = stack.enter_context(patch("daemon.src.state_machine.set_usb_storage_allowed"))
        machine = ModeStateMachine(config, MagicMock())
        machine.current_mode = old_mode
        machine.request_reapply()
        machine.transition_to(target_mode, 0)
    assert machine.transition_status == "ready"
    usb.assert_called_once_with(True if setting is None else setting)
