"""Unit tests for gallosd workstation identity module."""

from daemon.src.identity import _find_matched_machine, _resolve_hostname


def test_resolve_hostname_direct():
    machine = {"pc_name": "lab-pc42"}
    assert _resolve_hostname(machine) == "lab-pc42"


def test_resolve_hostname_room_and_number():
    machine = {"room": "lab-a", "pc_number": "15"}
    assert _resolve_hostname(machine) == "lab-a-pc15"


def test_find_matched_machine_from_config():
    config = {
        "machines": [
            {"mac": "aa:bb:cc:dd:ee:ff", "pc_name": "pc-01", "team_name": "Los Gallos"},
            {"mac": "11:22:33:44:55:66", "pc_name": "pc-02", "team_name": "Team 2"},
        ]
    }
    matched = _find_matched_machine(config, {}, ["aa:bb:cc:dd:ee:ff"])
    assert matched is not None
    assert matched["pc_name"] == "pc-01"
    assert matched["team_name"] == "Los Gallos"


def test_resolve_default_hostname_from_branding():
    from daemon.src.identity import _resolve_default_hostname

    assert _resolve_default_hostname({"branding": {"hostname": "ICPC"}}) == "ICPC"
    assert _resolve_default_hostname({"branding": {"hostname": "UAA"}}) == "UAA"
    assert _resolve_default_hostname({"branding": {"hostname": "GALLOS"}}) == "GALLOS"


def test_resolve_default_hostname_fallback_when_missing():
    from daemon.src.identity import _resolve_default_hostname

    assert _resolve_default_hostname({}) == "gallos"
    assert _resolve_default_hostname({"branding": {}}) == "gallos"
    assert _resolve_default_hostname({"branding": {"hostname": ""}}) == "gallos"


def test_resolve_default_hostname_rejects_oversized():
    from daemon.src.identity import _resolve_default_hostname

    oversized = "a" * 64
    assert _resolve_default_hostname({"branding": {"hostname": oversized}}) == "gallos"


def test_set_system_hostname_updates_effective_hostname():
    from subprocess import CompletedProcess
    from unittest.mock import patch

    from daemon.src.identity import _set_system_hostname

    with patch(
        "daemon.src.identity.subprocess.run",
        return_value=CompletedProcess(args=[], returncode=0, stderr=""),
    ) as run:
        _set_system_hostname("ICPC")

    run.assert_called_once_with(
        ["hostnamectl", "set-hostname", "ICPC"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_set_system_hostname_reports_failure():
    from unittest.mock import Mock, patch

    import pytest

    from daemon.src.identity import _set_system_hostname

    with patch(
        "daemon.src.identity.subprocess.run", return_value=Mock(returncode=1, stderr="denied")
    ):
        with pytest.raises(RuntimeError, match="denied"):
            _set_system_hostname("ICPC")


def test_apply_machine_identity_applies_branding_hostname():
    from unittest.mock import patch

    from daemon.src.identity import apply_machine_identity

    config = {"branding": {"hostname": "ICPC"}}
    with (
        patch("daemon.src.identity.get_local_mac_addresses", return_value=["11:22:33:44:55:66"]),
        patch("daemon.src.identity._set_system_hostname") as mock_set_host,
        patch("daemon.src.identity._write_identity_env") as mock_write_env,
    ):
        apply_machine_identity(config, {})
        mock_set_host.assert_called_once_with("ICPC")
        mock_write_env.assert_called_once_with(
            "/run/gallos/identity.env", "ICPC", "Contestant", "Default", "Main"
        )


def test_apply_machine_identity_applies_matched_pc_name():
    from unittest.mock import patch

    from daemon.src.identity import apply_machine_identity

    config = {
        "branding": {"hostname": "ICPC"},
        "machines": [{"mac": "aa:bb:cc:dd:ee:ff", "pc_name": "lab-pc01", "team_name": "Team A"}],
    }
    with (
        patch("daemon.src.identity.get_local_mac_addresses", return_value=["aa:bb:cc:dd:ee:ff"]),
        patch("daemon.src.identity._set_system_hostname") as mock_set_host,
        patch("daemon.src.identity._write_identity_env") as mock_write_env,
    ):
        apply_machine_identity(config, {})
        mock_set_host.assert_called_once_with("lab-pc01")
        mock_write_env.assert_called_once_with(
            "/run/gallos/identity.env", "lab-pc01", "Team A", "", ""
        )
