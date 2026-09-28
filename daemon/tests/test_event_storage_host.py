"""The storage helper must act only on a verified optional ext4 partition."""

import os
import stat
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from daemon.src.event_storage_host import mount_event_data, unmount_event_data


def test_mount_rejects_workspace_symlink_without_changing_target(tmp_path):
    mountpoint = tmp_path / "mount"
    target = tmp_path / "outside"
    mountpoint.mkdir()
    target.mkdir(mode=0o755)
    workspace = mountpoint / "contestant"
    workspace.symlink_to(target, target_is_directory=True)
    original_mode = stat.S_IMODE(target.stat().st_mode)
    lookup = MagicMock(stdout="/dev/sdb2\n", returncode=0)
    ext4 = MagicMock(stdout="ext4\n", returncode=0)
    source = MagicMock(stdout="/dev/sdb2\n", returncode=0)

    with (
        patch("daemon.src.event_storage_host.MOUNTPOINT", str(mountpoint)),
        patch("daemon.src.event_storage_host.WORKSPACE", str(workspace)),
        patch("daemon.src.event_storage_host._run", side_effect=[lookup, ext4, source]),
        patch(
            "daemon.src.event_storage_host.pwd.getpwnam",
            return_value=SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid()),
        ),
        pytest.raises(OSError),
    ):
        mount_event_data()

    assert stat.S_IMODE(target.stat().st_mode) == original_mode


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
