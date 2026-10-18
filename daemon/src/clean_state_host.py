"""Clear contestant-owned volatile storage in the Live host mount namespace."""

import json
import os
import pwd
import stat
import subprocess
import sys
from pathlib import Path

HOME = Path("/home/contestant")
VOLATILE_FILESYSTEMS = {"overlay", "tmpfs", "ramfs"}
KERNEL_FILESYSTEMS = {
    "proc",
    "sysfs",
    "devtmpfs",
    "devpts",
    "cgroup",
    "cgroup2",
    "mqueue",
    "securityfs",
    "debugfs",
    "tracefs",
    "configfs",
    "efivarfs",
    "pstore",
    "bpf",
    "binfmt_misc",
    "hugetlbfs",
    "fusectl",
    "rpc_pipefs",
    "autofs",
    "nsfs",
}
BOOT_PATHS = (Path("/cdrom"), Path("/isodevice"), Path("/rofs"), Path("/casper"))


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=60)


def mount_inventory() -> list[dict[str, str]]:
    return json.loads(
        _run(
            "findmnt", "--json", "--list", "--output", "TARGET,FSTYPE,OPTIONS,FSROOT,MAJ:MIN"
        ).stdout
    )["filesystems"]


def cleanup_roots(mounts: list[dict[str, str]]) -> list[Path]:
    """Refuse installed systems; only the Live volatile filesystems may be erased."""
    root = next((mount for mount in mounts if mount["target"] == "/"), None)
    if (
        not root
        or root["fstype"] not in VOLATILE_FILESYSTEMS
        or "rw" not in root["options"].split(",")
    ):
        raise RuntimeError("Contest cleanup requires a writable volatile Live root filesystem")
    roots = []
    identities = set()
    for mount in mounts:
        target = Path(mount["target"])
        if mount["fstype"] not in VOLATILE_FILESYSTEMS:
            continue
        identity = mount["maj:min"]
        if mount["fsroot"] != "/" or identity in identities:
            raise RuntimeError(f"Ambiguous volatile mount alias must be detached: {target}")
        identities.add(identity)
        if "rw" not in mount["options"].split(","):
            continue
        if (
            target == Path("/dev")
            or target.is_relative_to("/proc")
            or target.is_relative_to("/sys")
        ):
            continue
        if target.is_relative_to("/dev") and not target.is_relative_to("/dev/shm"):  # noqa: S108
            continue
        roots.append(target)
    return sorted(set(roots), key=lambda path: len(path.parts), reverse=True)


def _data_mounts(mounts: list[dict[str, str]]) -> list[Path]:
    return sorted(
        {
            Path(mount["target"])
            for mount in mounts
            if mount["fstype"] not in VOLATILE_FILESYSTEMS | KERNEL_FILESYSTEMS
            and not any(Path(mount["target"]).is_relative_to(boot) for boot in BOOT_PATHS)
        },
        key=lambda path: len(path.parts),
        reverse=True,
    )


def detach_data_mounts() -> list[dict[str, str]]:
    mounts = mount_inventory()
    cleanup_roots(mounts)  # Validate Live context before any host mutation.
    for target in _data_mounts(mounts):
        _run("umount", "--", str(target))
    current = mount_inventory()
    if _data_mounts(current):
        raise RuntimeError("Data filesystems remain mounted during Contest reset")
    cleanup_roots(current)
    return current


def _walk_owned(
    fd: int, directory: Path, uid: int, blocked: set[Path], protected: set[Path], delete: bool
) -> None:
    with os.scandir(fd) as entries:
        for entry in entries:
            path = directory / entry.name
            if path in blocked:
                continue
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                _visit_directory(fd, path, uid, blocked, protected, delete, info)
            elif info.st_uid == uid:
                if not delete:
                    raise RuntimeError(f"Contestant-owned files remain: {path}")
                os.unlink(entry.name, dir_fd=fd)


def _visit_directory(
    parent_fd: int,
    path: Path,
    uid: int,
    blocked: set[Path],
    protected: set[Path],
    delete: bool,
    expected: os.stat_result,
) -> None:
    fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    try:
        actual = os.fstat(fd)
        if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
            raise RuntimeError(f"Directory changed during cleanup: {path}")
        if actual.st_dev != os.fstat(parent_fd).st_dev:
            raise RuntimeError(f"Unexpected mount during cleanup: {path}")
        _walk_owned(fd, path, uid, blocked, protected, delete)
        if actual.st_uid == uid and path not in protected:
            if not delete:
                raise RuntimeError(f"Contestant-owned directories remain: {path}")
            os.rmdir(path.name, dir_fd=parent_fd)
    finally:
        os.close(fd)


def cleanup_owned_files(
    root: Path,
    uid: int,
    mounts: set[Path],
    home: Path,
    backing_paths: set[Path] | None = None,
) -> None:
    """Never follow links, cross filesystems or remove system-owned entries."""
    subtrees = {home} | (backing_paths or set())
    blocked = (mounts - {root}) | subtrees
    protected = {parent for path in blocked for parent in path.parents}
    if any(root.is_relative_to(path) for path in subtrees):
        return
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _walk_owned(fd, root, uid, blocked, protected, True)
        _walk_owned(fd, root, uid, blocked, protected, False)
    finally:
        os.close(fd)


def overlay_backing_paths(mounts: list[dict[str, str]]) -> set[Path]:
    """Never modify a mounted overlay's lower/upper/work trees directly."""
    paths = set()
    for mount in mounts:
        if mount["fstype"] != "overlay":
            continue
        for option in mount["options"].split(","):
            key, separator, value = option.partition("=")
            if separator and key in {"upperdir", "lowerdir", "workdir"}:
                paths.update(Path(path) for path in value.split(":") if path.startswith("/"))
    return paths


def main() -> None:
    uid = pwd.getpwnam("contestant").pw_uid
    if uid == 0:
        raise RuntimeError("Refusing to clean files for UID 0")
    mounts = detach_data_mounts()
    targets = {Path(mount["target"]) for mount in mounts}
    backing = overlay_backing_paths(mounts)
    for root in cleanup_roots(mounts):
        cleanup_owned_files(root, uid, targets, HOME, backing)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
