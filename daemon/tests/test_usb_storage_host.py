"""USB lockdown must remove existing mounts without disrupting live media or HID."""

import json
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from daemon.src import usb_manager


def test_host_service_failure_blocks_contest():
    with patch(
        "daemon.src.usb_manager.subprocess.run",
        return_value=SimpleNamespace(returncode=1, stderr="busy USB filesystem"),
    ):
        with pytest.raises(RuntimeError, match="busy USB filesystem"):
            usb_manager.set_usb_storage_allowed(False)


def _host():
    from daemon.src import usb_storage_host

    return usb_storage_host


@pytest.fixture
def sysfs(tmp_path, monkeypatch):
    host = _host()
    bus = tmp_path / "bus"
    blocks = tmp_path / "block"
    bus.mkdir()
    blocks.mkdir()
    monkeypatch.setattr(host, "USB_DEVICES", bus)
    monkeypatch.setattr(host, "BLOCK_DEVICES", blocks)
    monkeypatch.setattr(host, "DRIVERS_PROBE", tmp_path / "drivers_probe")

    def interface(name, usb_class="08"):
        path = tmp_path / "devices" / name.split(":")[0] / name
        path.mkdir(parents=True)
        (path / "bInterfaceClass").write_text(usb_class)
        (path / "authorized").write_text("1\n")
        (bus / name).symlink_to(path, target_is_directory=True)
        return path

    return host, blocks, interface


def test_revoke_and_restore_real_interface_symlinks_preserves_hid(sysfs):
    host, _, interface = sysfs
    storage = interface("1-2:1.0")
    hid = interface("1-2:1.1", "03")
    host._revoke_existing_usb_storage(set())
    assert (storage / "authorized").read_text().strip() == "0"
    assert (hid / "authorized").read_text().strip() == "1"
    host._restore_usb_storage()
    assert (storage / "authorized").read_text().strip() == "1"
    assert host.DRIVERS_PROBE.read_text().strip() == "1-2:1.0"


def test_boot_interface_remains_authorized(sysfs):
    host, blocks, interface = sysfs
    boot = interface("1-2:1.0")
    other = interface("1-3:1.0")
    partition = boot / "host0" / "block" / "sdb" / "sdb1"
    partition.mkdir(parents=True)
    (blocks / "8:17").symlink_to(partition, target_is_directory=True)
    host._revoke_existing_usb_storage({"8:17"})
    assert (boot / "authorized").read_text().strip() == "1"
    assert (other / "authorized").read_text().strip() == "0"


def test_missing_boot_device_mapping_fails_closed(sysfs):
    host, _, _ = sysfs
    with pytest.raises(FileNotFoundError):
        host._revoke_existing_usb_storage({"8:17"})


def _inventory_runner(mounts, *, busy=False):
    devices = {
        "blockdevices": [
            {
                "name": "/dev/sdb",
                "tran": "usb",
                "maj:min": "8:16",
                "children": [
                    {"name": "/dev/sdb1", "tran": None, "maj:min": "8:17"},
                    {"name": "/dev/sdb2", "tran": None, "maj:min": "8:18"},
                ],
            },
            {"name": "/dev/nvme0n1", "tran": "nvme", "maj:min": "259:0"},
        ]
    }

    def run(argv, **_kwargs):
        if argv[0] == "lsblk":
            return SimpleNamespace(stdout=json.dumps(devices))
        if argv[0] == "findmnt":
            return SimpleNamespace(stdout=json.dumps({"filesystems": list(mounts)}))
        if argv[0] == "umount":
            if busy:
                raise subprocess.CalledProcessError(32, argv, stderr="busy")
            target = argv[-1]
            assert not any(m["target"].startswith(target + "/") for m in mounts)
            mounts[:] = [m for m in mounts if m["target"] != target]
            return SimpleNamespace(stdout="")
        raise AssertionError(argv)

    return run


def test_unmount_inherits_usb_transport_and_handles_bind_mounts_and_spaces():
    host = _host()
    mounts = [
        {"target": "/cdrom", "maj:min": "8:17"},
        {"target": "/media/notes with spaces", "maj:min": "8:18"},
        {"target": "/media/notes with spaces/nested", "maj:min": "8:18"},
        {"target": "/tmp/bound-notes", "maj:min": "8:18"},
        {"target": "/home", "maj:min": "259:0"},
    ]
    with patch.object(host.subprocess, "run", side_effect=_inventory_runner(mounts)):
        protected = host._unmount_existing_usb_storage()
    assert protected == {"8:16", "8:17"}
    assert {m["target"] for m in mounts} == {"/cdrom", "/home"}


def test_busy_usb_mount_aborts_without_revoking(sysfs):
    host, _, interface = sysfs
    storage = interface("1-3:1.0")
    mounts = [{"target": "/media/notes", "maj:min": "8:18"}]
    with patch.object(host.subprocess, "run", side_effect=_inventory_runner(mounts, busy=True)):
        with pytest.raises(subprocess.CalledProcessError):
            host._lock_existing_storage()
    assert (storage / "authorized").read_text().strip() == "1"


def test_policy_roundtrip_removes_mount_then_restores_interface(sysfs, tmp_path, monkeypatch):
    host, _, interface = sysfs
    storage = interface("1-3:1.0")
    monkeypatch.setattr(host, "POLKIT_RULE_FILE", tmp_path / "polkit" / "block.rules")
    monkeypatch.setattr(host, "UDEV_RULE_FILE", tmp_path / "udev" / "block.rules")
    mounts = [{"target": "/media/notes", "maj:min": "8:18"}]
    inventory = _inventory_runner(mounts)

    def run(argv, **kwargs):
        if argv[0] == "udevadm":
            return SimpleNamespace(stdout="")
        return inventory(argv, **kwargs)

    with patch.object(host.subprocess, "run", side_effect=run):
        host.apply_usb_policy(False)
        assert mounts == []
        assert (storage / "authorized").read_text().strip() == "0"
        assert 'ENV{DEVTYPE}=="usb_interface"' in host.UDEV_RULE_FILE.read_text()
        assert host.POLKIT_RULE_FILE.is_file()
        host.apply_usb_policy(True)
    assert not host.POLKIT_RULE_FILE.exists()
    assert not host.UDEV_RULE_FILE.exists()
    assert (storage / "authorized").read_text().strip() == "1"
    assert host.DRIVERS_PROBE.read_text().strip() == "1-3:1.0"
