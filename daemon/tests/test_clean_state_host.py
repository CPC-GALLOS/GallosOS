"""Contest reset deletes only contestant data and never follows symlinks or mounts."""

import importlib
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


def host_module():
    return importlib.import_module("daemon.src.clean_state_host")


def test_cleanup_removes_real_preloaded_files_and_preserves_home_and_symlink_target(tmp_path):
    host = host_module()
    root = tmp_path / "live"
    home = root / "home" / "contestant"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "important").write_text("preserve")
    home.mkdir(parents=True)
    (home / "solution.cpp").write_text("handled by the separate home reset")
    for relative in ("tmp/stash.cpp", "var/tmp/.retained/notes", "dev/shm/notes", "run/lock/notes"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("preloaded")
    (root / "tmp" / "escape").symlink_to(outside, target_is_directory=True)
    host.cleanup_owned_files(root, os.getuid(), set(), home)
    assert (outside / "important").read_text() == "preserve"
    assert (home / "solution.cpp").is_file()
    assert not (root / "tmp" / "stash.cpp").exists()
    assert not (root / "var" / "tmp" / ".retained").exists()
    assert not (root / "dev" / "shm" / "notes").exists()
    assert not (root / "run" / "lock" / "notes").exists()


def test_cleanup_preserves_other_owners_and_mount_roots(tmp_path):
    host = host_module()
    data = tmp_path / "data"
    data.mkdir()
    retained = data / "service-owned"
    retained.write_text("preserve")
    host.cleanup_owned_files(data, os.getuid() + 1, set(), tmp_path / "home")
    assert retained.is_file()
    retained.unlink()
    mounted = data / "mounted[1]"
    mounted.mkdir()
    (mounted / "keep").write_text("mounted filesystem contents")
    host.cleanup_owned_files(data, os.getuid(), {mounted}, tmp_path / "home")
    assert mounted.is_dir()
    assert (mounted / "keep").is_file()


def test_cleanup_failure_propagates(tmp_path):
    host = host_module()
    (tmp_path / "retained").write_text("preloaded")
    with patch.object(host.os, "unlink", side_effect=OSError("cannot delete")):
        with pytest.raises(OSError, match="cannot delete"):
            host.cleanup_owned_files(tmp_path, os.getuid(), set(), tmp_path / "home")


def test_cleanup_rejects_remaining_owned_files(tmp_path):
    host = host_module()
    (tmp_path / "retained").write_text("preloaded")
    with patch.object(host.os, "unlink"):
        with pytest.raises(RuntimeError, match="remain"):
            host.cleanup_owned_files(tmp_path, os.getuid(), set(), tmp_path / "home")


def test_only_live_volatile_filesystems_are_cleaned():
    host = host_module()
    mounts = [
        {"target": "/", "fstype": "overlay", "options": "rw,relatime"},
        {"target": "/tmp", "fstype": "tmpfs", "options": "rw,nosuid"},
        {"target": "/run", "fstype": "tmpfs", "options": "rw,nosuid"},
        {"target": "/dev", "fstype": "devtmpfs", "options": "rw"},
        {"target": "/dev/shm", "fstype": "tmpfs", "options": "rw"},
        {"target": "/rofs", "fstype": "squashfs", "options": "ro"},
        {"target": "/cdrom", "fstype": "iso9660", "options": "ro"},
        {"target": "/proc", "fstype": "proc", "options": "rw"},
    ]
    for number, mount in enumerate(mounts):
        mount.update({"fsroot": "/", "maj:min": f"0:{number}"})
    assert set(host.cleanup_roots(mounts)) == {
        Path("/"),
        Path("/tmp"),
        Path("/run"),
        Path("/dev/shm"),
    }
    mounts[0]["fstype"] = "ext4"
    with pytest.raises(RuntimeError, match="Live"):
        host.cleanup_roots(mounts)


def test_data_volumes_are_unmounted_and_not_erased():
    host = host_module()
    base = [{"target": "/", "fstype": "overlay", "options": "rw", "fsroot": "/", "maj:min": "0:1"}]
    data = {"target": "/media/notes", "fstype": "ext4", "options": "rw"}
    with (
        patch.object(host, "mount_inventory", side_effect=[base + [data], base]),
        patch.object(host, "_run") as command,
    ):
        assert host.detach_data_mounts() == base
    command.assert_called_once_with("umount", "--", "/media/notes")


def test_busy_data_volume_aborts_reset():
    host = host_module()
    mounts = [
        {"target": "/", "fstype": "overlay", "options": "rw", "fsroot": "/", "maj:min": "0:1"},
        {"target": "/mnt/notes", "fstype": "ext4", "options": "ro"},
    ]
    with (
        patch.object(host, "mount_inventory", return_value=mounts),
        patch.object(host, "_run", side_effect=subprocess.CalledProcessError(32, "umount")),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            host.detach_data_mounts()


def test_overlay_backing_trees_are_preserved(tmp_path):
    host = host_module()
    upper = tmp_path / "cow" / "upper"
    upper.mkdir(parents=True)
    (upper / "overlay-metadata").write_text("must not modify backing tree directly")
    home = tmp_path / "home"
    mounts = [{"fstype": "overlay", "options": f"rw,upperdir={upper},workdir={tmp_path}/cow/work"}]
    backing = host.overlay_backing_paths(mounts)
    assert upper in backing
    host.cleanup_owned_files(tmp_path, os.getuid(), set(), home, backing)
    assert (upper / "overlay-metadata").is_file()


def test_persistent_root_is_rejected_before_detaching_volumes():
    host = host_module()
    with (
        patch.object(
            host,
            "mount_inventory",
            return_value=[
                {"target": "/", "fstype": "ext4", "options": "rw"},
                {"target": "/media/data", "fstype": "ext4", "options": "rw"},
            ],
        ),
        patch.object(host, "_run") as command,
    ):
        with pytest.raises(RuntimeError, match="Live"):
            host.detach_data_mounts()
    command.assert_not_called()


def test_host_service_failure_is_reported():
    from daemon.src.clean_state import reset_contest_scratch

    with patch(
        "daemon.src.clean_state.subprocess.run",
        return_value=SimpleNamespace(
            returncode=1,
            stderr="cleanup service failed",
        ),
    ) as command:
        with pytest.raises(RuntimeError, match="cleanup service failed"):
            reset_contest_scratch()
    assert command.call_args.args[0] == ["systemctl", "start", "gallos-clean-state.service"]


@pytest.mark.parametrize("fsroot,identity", [("/upper", "0:2"), ("/", "0:1")])
def test_volatile_bind_aliases_fail_closed(fsroot, identity):
    host = host_module()
    mounts = [
        {"target": "/", "fstype": "overlay", "options": "rw", "fsroot": "/", "maj:min": "0:1"},
        {
            "target": "/tmp/alias",
            "fstype": "overlay",
            "options": "ro",
            "fsroot": fsroot,
            "maj:min": identity,
        },
    ]
    with pytest.raises(RuntimeError, match="mount alias"):
        host.cleanup_roots(mounts)
