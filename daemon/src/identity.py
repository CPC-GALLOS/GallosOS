"""Machine identity and workstation mapping module for GallosOS Daemon.

Maps local MAC addresses against machine.toml or machines[] table in gallos.toml,
sets the workstation hostname, and exports /run/gallos/identity.env for desktop display.
"""

import contextlib
import glob
import os
import subprocess
import sys
from typing import Any


def get_local_mac_addresses() -> list[str]:
    """Scans sysfs for all active Ethernet/WLAN hardware MAC addresses."""
    macs: list[str] = []
    for addr_file in glob.glob("/sys/class/net/*/address"):
        if "lo" in addr_file:
            continue
        with contextlib.suppress(OSError):
            with open(addr_file, encoding="utf-8") as f:
                mac = f.read().strip().lower()
                if mac and mac != "00:00:00:00:00:00":
                    macs.append(mac)
    return macs


def _find_matched_machine(
    config: dict[str, Any], machine_cfg: dict[str, Any], local_macs: list[str]
) -> dict[str, Any] | None:
    """Matches machine table entry based on machine_cfg or local MAC addresses."""
    if isinstance(machine_cfg, dict) and "machine" in machine_cfg:
        return machine_cfg["machine"]

    machines_list = config.get("machines", [])
    for entry in machines_list:
        mac = entry.get("mac", "").strip().lower()
        if mac in local_macs:
            return entry
    return None


def _resolve_hostname(machine: dict[str, Any]) -> str:
    """Derives the workstation hostname from machine metadata."""
    if pc_name := machine.get("pc_name"):
        return str(pc_name)
    room = machine.get("room", "")
    pc_number = machine.get("pc_number", "")
    if room and pc_number:
        return f"{room}-pc{pc_number}"
    if pc_number:
        return f"contestant-pc{pc_number}"
    return "gallos-workstation"


def _resolve_default_hostname(config: dict[str, Any]) -> str:
    """Resolves event-level white-label hostname from branding, falling back to 'gallos'."""
    branding = config.get("branding", {})
    if isinstance(branding, dict):
        if custom_host := branding.get("hostname"):
            custom_host_str = str(custom_host).strip()
            if custom_host_str and len(custom_host_str) <= 63:
                return custom_host_str
    return "gallos"


def _set_system_hostname(hostname: str) -> None:
    """Set the transient hostname through systemd outside the daemon sandbox."""
    result = subprocess.run(
        ["hostnamectl", "--transient", "set-hostname", hostname],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip() or f"hostnamectl exited {result.returncode}"
        print(f"[identity] Could not set transient hostname: {message}", file=sys.stderr)


def _write_identity_env(filepath: str, hostname: str, team: str, seat: str, room: str) -> None:
    """Writes /run/gallos/identity.env runtime environment file."""
    content = (
        f"GALLOS_HOSTNAME={hostname}\n"
        f"GALLOS_TEAM_NAME={team}\n"
        f"GALLOS_SEAT_LABEL={seat}\n"
        f"GALLOS_ROOM={room}\n"
    )
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"[identity] Warning: Could not write identity file: {e}", file=sys.stderr)


def apply_machine_identity(config: dict[str, Any], machine_cfg: dict[str, Any]) -> None:
    """Matches machine table and exports identity metadata."""
    local_macs = get_local_mac_addresses()
    print(f"[identity] Probed hardware interfaces (found {len(local_macs)} MAC addresses).")

    try:
        os.makedirs("/run/gallos", exist_ok=True)
    except Exception as e:
        print(f"[identity] Warning: Could not create runtime directory: {e}", file=sys.stderr)

    identity_file = "/run/gallos/identity.env"

    matched = _find_matched_machine(config, machine_cfg, local_macs)
    if matched:
        hostname = _resolve_hostname(matched)
        team = matched.get("team_name", "")
        seat = matched.get("seat_label", "")
        room = matched.get("room", "")
        print(
            f"[identity] Assigned Workstation Identity: "
            f"Hostname='{hostname}', Team='{team}', Seat='{seat}'"
        )
        _set_system_hostname(hostname)
        _write_identity_env(identity_file, hostname, team, seat, room)
    else:
        fallback_host = _resolve_default_hostname(config)
        print(f"[identity] No MAC mapping matched. Applying event hostname: '{fallback_host}'")
        _set_system_hostname(fallback_host)
        _write_identity_env(identity_file, fallback_host, "Contestant", "Default", "Main")
