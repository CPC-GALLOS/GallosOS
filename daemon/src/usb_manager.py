"""USB Mass Storage Lockdown & Post-Contest Unlock module for GallosOS Daemon.

Implements Polkit JavaScript rule (primary) and Udev authorized=0 (fallback)
to deny external USB storage during Contest mode, and re-authorizes it upon
contest completion for contestant code export.
"""

import os
import stat
import subprocess

POLKIT_RULES_DIR = "/etc/polkit-1/rules.d"
POLKIT_RULE_FILE = os.path.join(POLKIT_RULES_DIR, "99-gallos-usb-block.rules")

UDEV_RULES_DIR = "/etc/udev/rules.d"
UDEV_RULE_FILE = os.path.join(UDEV_RULES_DIR, "99-contest-usb-block.rules")

POLKIT_JS_RULE = """// GallosOS Dynamic USB Storage Denial Rule
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.udisks2.") === 0 && subject.user === "contestant") {
        return polkit.Result.NO;
    }
});
"""

UDEV_STORAGE_BLOCK_RULE = (
    'ACTION=="add", SUBSYSTEM=="usb", DEVTYPE=="usb_device", '
    'ATTRS{bInterfaceClass}=="08", ATTR{authorized}="0"\n'
)


def _write_rule_file(filepath: str, content: str) -> None:
    """Safely writes a system rule file with standard read-only non-root permissions."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    fd = os.open(filepath, flags, mode)
    with open(fd, "w", encoding="utf-8") as f:
        f.write(content)


def set_usb_storage_allowed(allowed: bool) -> None:
    """Configures Polkit and Udev to allow or block USB mass-storage."""
    os.makedirs(POLKIT_RULES_DIR, exist_ok=True)
    os.makedirs(UDEV_RULES_DIR, exist_ok=True)

    if allowed:
        # Re-authorize USB mass storage
        print("[usb_manager] Unlocking USB mass-storage for code extraction.")
        if os.path.exists(POLKIT_RULE_FILE):
            os.remove(POLKIT_RULE_FILE)
        if os.path.exists(UDEV_RULE_FILE):
            os.remove(UDEV_RULE_FILE)
    else:
        # Block USB mass storage
        print("[usb_manager] Locking USB mass-storage (Contest mode active).")
        _write_rule_file(POLKIT_RULE_FILE, POLKIT_JS_RULE)
        _write_rule_file(UDEV_RULE_FILE, UDEV_STORAGE_BLOCK_RULE)
    result = subprocess.run(
        ["udevadm", "control", "--reload-rules"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"udev rule reload failed: {result.stderr.strip()}")
