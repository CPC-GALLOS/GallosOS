"""The storage helper must act only on a verified optional ext4 partition."""

from unittest.mock import MagicMock, patch

import pytest

from daemon.src.event_storage_host import mount_event_data, unmount_event_data


def test_mount_rejects_duplicate_label_before_mounting():
    devices = MagicMock(stdout="/dev/sdb2\n/dev/sdc2\n", returncode=0)
    with patch("subprocess.run", return_value=devices) as command:
        with pytest.raises(RuntimeError, match="more than one"):
            mount_event_data()
    assert command.call_count == 1


def test_mount_rejects_non_ext4_partition():
    devices = MagicMock(stdout="/dev/sdb2\n", returncode=0)
    wrong_type = MagicMock(stdout="vfat\n", returncode=0)
    with patch("subprocess.run", side_effect=[devices, wrong_type]) as command:
        with pytest.raises(RuntimeError, match="ext4"):
            mount_event_data()
    assert command.call_count == 2


def test_unmount_failure_is_reported():
    mounted = MagicMock(stdout="/dev/sdb2\n", returncode=0)
    failure = MagicMock(stderr="target is busy", returncode=32)
    with patch("subprocess.run", side_effect=[mounted, failure]):
        with pytest.raises(RuntimeError, match="busy"):
            unmount_event_data()
