"""The daemon delegates optional storage to the host systemd service."""

from unittest.mock import MagicMock, patch

import pytest

from daemon.src.storage import mount_event_data, unmount_event_data


def test_mount_reports_host_visible_partition():
    started = MagicMock(returncode=0)
    visible = MagicMock(returncode=0, stdout="/dev/sdb2\n")
    with patch("subprocess.run", side_effect=[started, visible]):
        assert mount_event_data() is True


def test_missing_optional_partition_is_reported():
    started = MagicMock(returncode=0)
    absent = MagicMock(returncode=1, stdout="")
    with patch("subprocess.run", side_effect=[started, absent]):
        assert mount_event_data() is False


def test_mount_service_failure_blocks_transition():
    failed = MagicMock(returncode=1, stderr="unit failed")
    with patch("subprocess.run", return_value=failed):
        with pytest.raises(RuntimeError, match="unit failed"):
            mount_event_data()


def test_busy_unmount_blocks_transition():
    busy = MagicMock(returncode=1, stderr="target is busy")
    with patch("subprocess.run", return_value=busy):
        with pytest.raises(RuntimeError, match="busy"):
            unmount_event_data()


def test_unmount_rearms_failed_service_before_stopping_existing_mount():
    visible = MagicMock(returncode=0, stdout="/dev/sda\n")
    started = MagicMock(returncode=0)
    stopped = MagicMock(returncode=0)
    absent = MagicMock(returncode=1, stdout="")
    with patch("subprocess.run", side_effect=[visible, started, stopped, absent]) as run:
        unmount_event_data()
    assert run.call_args_list[1].args[0] == ["systemctl", "start", "gallos-event-storage.service"]
    assert run.call_args_list[2].args[0] == ["systemctl", "stop", "gallos-event-storage.service"]
