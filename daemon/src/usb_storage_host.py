"""Host-namespace USB mount isolation and mass-storage interface authorization."""

import json
import subprocess
import sys
from pathlib import Path

USB_DEVICES = Path("/sys/bus/usb/devices")
BLOCK_DEVICES = Path("/sys/dev/block")
DRIVERS_PROBE = Path("/sys/bus/usb/drivers_probe")
POLKIT_RULE_FILE = Path("/etc/polkit-1/rules.d/99-gallos-usb-block.rules")
UDEV_RULE_FILE = Path("/etc/udev/rules.d/99-contest-usb-block.rules")
PROTECTED_MOUNTS = {"/", "/usr", "/boot", "/boot/efi", "/cdrom", "/isodevice"}

POLKIT_JS_RULE = """// GallosOS Contest storage denial
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.udisks2.") === 0 && subject.user === "contestant") {
        return polkit.Result.NO;
    }
});
"""
UDEV_STORAGE_BLOCK_RULE = (
    'ACTION=="add", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_interface", '
    'ATTR{bInterfaceClass}=="08", ATTR{authorized}="0"\n'
)


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=15)


def _usb_block_ids(
    nodes: list[dict], inherited_usb: bool = False, ancestors: set[str] | None = None
) -> dict[str, set[str]]:
    """Follow disk ancestry: partitions need not repeat their parent's TRAN."""
    identities: dict[str, set[str]] = {}
    for node in nodes:
        usb = inherited_usb or node.get("tran") == "usb"
        ancestry = (ancestors or set()) | {node["maj:min"]}
        if usb:
            identities.setdefault(node["maj:min"], set()).update(ancestry)
        for identity, parents in _usb_block_ids(node.get("children", []), usb, ancestry).items():
            identities.setdefault(identity, set()).update(parents)
    return identities


def _usb_mount_inventory() -> tuple[set[str], set[str]]:
    devices = json.loads(_run("lsblk", "--json", "--paths", "--output", "NAME,TRAN,MAJ:MIN").stdout)
    usb_ids = _usb_block_ids(devices["blockdevices"])
    mounts = json.loads(_run("findmnt", "--json", "--list", "--output", "TARGET,MAJ:MIN").stdout)
    targets, protected = set(), set()
    for mount in mounts["filesystems"]:
        if mount["maj:min"] not in usb_ids:
            continue
        if mount["target"] in PROTECTED_MOUNTS:
            protected.update(usb_ids[mount["maj:min"]])
        else:
            targets.add(mount["target"])
    return targets, protected


def _unmount_existing_usb_storage() -> set[str]:
    """Unmount every non-system USB mount, including bind mounts and nested paths."""
    targets, protected = _usb_mount_inventory()
    for target in sorted(targets, key=lambda value: (value.count("/"), value), reverse=True):
        _run("umount", "--", target)
    remaining, current_protected = _usb_mount_inventory()
    if remaining:
        raise RuntimeError(f"USB filesystems remained mounted: {sorted(remaining)}")
    return protected | current_protected


def _storage_interfaces() -> list[Path]:
    """Resolve the bus symlink before accessing interface attributes."""
    return sorted(
        class_file.resolve(strict=True).parent
        for class_file in USB_DEVICES.glob("*/bInterfaceClass")
        if class_file.read_text(encoding="ascii").strip().lower() == "08"
    )


def _set_authorized(interface: Path, value: str) -> None:
    authorized = interface / "authorized"
    authorized.write_text(value + "\n", encoding="ascii")
    if authorized.read_text(encoding="ascii").strip() != value:
        raise RuntimeError(f"USB authorization did not change: {interface.name}")


def _revoke_existing_usb_storage(protected_ids: set[str]) -> None:
    boot_paths = [(BLOCK_DEVICES / identity).resolve(strict=True) for identity in protected_ids]
    for interface in _storage_interfaces():
        if any(path.is_relative_to(interface) for path in boot_paths):
            continue
        _set_authorized(interface, "0")


def _restore_usb_storage() -> None:
    restored = []
    for interface in _storage_interfaces():
        if (interface / "authorized").read_text(encoding="ascii").strip() == "0":
            _set_authorized(interface, "1")
            restored.append(interface.name)
    # The kernel requires an explicit probe after authorizing USB interfaces.
    for name in restored:
        DRIVERS_PROBE.write_text(name + "\n", encoding="ascii")


def _lock_existing_storage() -> None:
    protected = _unmount_existing_usb_storage()
    _revoke_existing_usb_storage(protected)


def apply_usb_policy(allowed: bool) -> None:
    """Install policy before inspecting mounts; propagate every enforcement failure."""
    if allowed:
        POLKIT_RULE_FILE.unlink(missing_ok=True)
        UDEV_RULE_FILE.unlink(missing_ok=True)
    else:
        for path, content in (
            (POLKIT_RULE_FILE, POLKIT_JS_RULE),
            (UDEV_RULE_FILE, UDEV_STORAGE_BLOCK_RULE),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            path.chmod(0o644)
    _run("udevadm", "control", "--reload-rules")
    _run("udevadm", "settle", "--timeout=10")
    if allowed:
        _restore_usb_storage()
    else:
        _lock_existing_storage()


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"lock", "unlock"}:
        raise SystemExit("usage: usb_storage_host lock|unlock")
    try:
        apply_usb_policy(sys.argv[1] == "unlock")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(130)
