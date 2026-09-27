"""Unit tests for gallos-daemon config ingestion module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import mock_open, patch

from daemon.src.config import (
    DEFAULT_CONFIG,
    _load_cmdline_config,
    fetch_remote_config,
    get_cmdline_config_param,
    is_config_expired,
    load_active_config,
    load_local_config,
    load_machine_config,
    resolve_config_path,
)


def test_default_config_structure():
    assert "version" in DEFAULT_CONFIG
    assert "mode" in DEFAULT_CONFIG
    assert "global" in DEFAULT_CONFIG
    assert "contest" in DEFAULT_CONFIG
    assert "default" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["mode"] == "Default"


def test_is_config_expired_not_set():
    config = {"global": {}}
    assert is_config_expired(config) is False


def test_is_config_expired_future():
    future_dt = datetime.now(timezone.utc) + timedelta(days=1)
    config = {"global": {"config_expiration": future_dt.isoformat()}}
    assert is_config_expired(config) is False


def test_is_config_expired_past():
    past_dt = datetime.now(timezone.utc) - timedelta(days=1)
    config = {"global": {"config_expiration": past_dt.isoformat()}}
    assert is_config_expired(config) is True


def test_get_cmdline_config_param():
    mock_cmdline = (
        "BOOT_IMAGE=/casper/vmlinuz boot=casper gallos.config=http://192.168.1.10/gallos.toml quiet"
    )
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=mock_cmdline)),
    ):
        param = get_cmdline_config_param()
        assert param == "http://192.168.1.10/gallos.toml"


def test_fetch_remote_config_rejects_non_http():
    assert fetch_remote_config("ftp://example.com/gallos.toml") is None
    assert fetch_remote_config("file:///etc/gallos.toml") is None


def test_load_active_config_ignores_remote_recovery_hash():
    """recovery.root_password_hash must never come from a remote/cmdline-fetched config."""
    remote_config = {
        "mode": "Default",
        "global": {},
        "recovery": {"root_password_hash": "$6$leaked$fromremote"},
    }
    with (
        patch("daemon.src.config.get_cmdline_config_param", return_value="http://x/gallos.toml"),
        patch(
            "daemon.src.config._load_cmdline_config",
            return_value=(remote_config, "remote (http://x/gallos.toml)"),
        ),
        patch(
            "daemon.src.config.load_local_config",
            return_value=(
                {"recovery": {"root_password_hash": "$6$local$hash"}},
                "/boot/gallos/gallos.toml",
            ),
        ),
    ):
        result = load_active_config()
        assert result["recovery"]["root_password_hash"] == "$6$local$hash"


def test_load_local_config_prefers_boot_gallos_config_dir():
    """The 55gallos-live /boot/gallos symlink target must win over flat-path fallbacks."""
    toml_bytes = b'mode = "Default"\n'
    with (
        patch(
            "os.path.isfile",
            side_effect=lambda p: p == "/boot/gallos/config/gallos.toml",
        ),
        patch("builtins.open", mock_open(read_data=toml_bytes)),
    ):
        data, source = load_local_config()
        assert source == "/boot/gallos/config/gallos.toml"
        assert data["mode"] == "Default"


def test_load_local_config_falls_back_to_ventoy_path():
    toml_bytes = b'mode = "Default"\n'
    with (
        patch(
            "os.path.isfile",
            side_effect=lambda p: p == "/gallos/gallos.toml",
        ),
        patch("builtins.open", mock_open(read_data=toml_bytes)),
    ):
        _, source = load_local_config()
        assert source == "/gallos/gallos.toml"


def test_load_machine_config_prefers_boot_gallos_config_dir():
    toml_bytes = b'hostname = "seat-04"\n'
    with (
        patch(
            "os.path.isfile",
            side_effect=lambda p: p == "/boot/gallos/config/machine.toml",
        ),
        patch("builtins.open", mock_open(read_data=toml_bytes)),
    ):
        data = load_machine_config()
        assert data["hostname"] == "seat-04"


def test_load_active_config_no_local_recovery_hash_defaults_to_none():
    with (
        patch("daemon.src.config.get_cmdline_config_param", return_value=None),
        patch("daemon.src.config.load_local_config", return_value=(None, "")),
    ):
        result = load_active_config()
        assert result["recovery"]["root_password_hash"] is None


def test_resolve_config_path_variants(tmp_path):
    config_dir = tmp_path / "boot" / "gallos"
    config_dir.mkdir(parents=True)
    target_file = config_dir / "codeforces-training.gallos.toml"
    target_file.write_text('mode = "Event"\n', encoding="utf-8")

    search_dirs = [str(config_dir)]

    # Exact filename with .gallos.toml
    assert resolve_config_path("codeforces-training.gallos.toml", search_dirs=search_dirs) == str(
        target_file
    )
    # Stem without extension
    assert resolve_config_path("codeforces-training", search_dirs=search_dirs) == str(target_file)
    # Stem with generic .toml extension
    assert resolve_config_path("codeforces-training.toml", search_dirs=search_dirs) == str(
        target_file
    )
    # Non-existent
    assert resolve_config_path("non-existent", search_dirs=search_dirs) is None


def test_load_cmdline_config_resolves_relative_profile(tmp_path):
    config_dir = tmp_path / "boot" / "gallos"
    config_dir.mkdir(parents=True)
    target_file = config_dir / "icpc-onsite.gallos.toml"
    target_file.write_text('mode = "Contest"\n', encoding="utf-8")

    data, source = _load_cmdline_config("icpc-onsite", search_dirs=[str(config_dir)])
    assert data is not None
    assert data["mode"] == "Contest"
    assert source == f"cmdline file ({target_file})"


def test_load_local_config_auto_discovers_unique_profile(tmp_path):
    config_dir = tmp_path / "boot" / "gallos"
    config_dir.mkdir(parents=True)
    target_file = config_dir / "maratona-sbc.gallos.toml"
    target_file.write_text('mode = "Contest"\n', encoding="utf-8")

    data, source = load_local_config(search_dirs=[str(config_dir)])
    assert data is not None
    assert data["mode"] == "Contest"
    assert source == str(target_file)


def test_load_local_config_prefers_unique_profile_over_bundled_baseline(tmp_path):
    iso_config = tmp_path / "boot" / "gallos" / "config"
    usb_config = tmp_path / "gallos"
    iso_config.mkdir(parents=True)
    usb_config.mkdir()
    (iso_config / "baseline").mkdir()
    (iso_config / "baseline" / "baseline.gallos.toml").write_text(
        'mode = "Contest"\n', encoding="utf-8"
    )
    profile = usb_config / "training.gallos.toml"
    profile.write_text('mode = "Event"\n', encoding="utf-8")

    data, source = load_local_config(search_dirs=[str(iso_config), str(usb_config)])

    assert data["mode"] == "Event"
    assert source == str(profile)


def test_load_local_config_prefers_organizer_canonical_over_named_profile(tmp_path):
    config_dir = tmp_path / "gallos"
    config_dir.mkdir()
    canonical = config_dir / "gallos.toml"
    canonical.write_text('mode = "Contest"\n', encoding="utf-8")
    (config_dir / "training.gallos.toml").write_text('mode = "Event"\n', encoding="utf-8")
    (config_dir / "baseline").mkdir()
    (config_dir / "baseline" / "baseline.gallos.toml").write_text(
        'mode = "Default"\n', encoding="utf-8"
    )

    data, source = load_local_config(search_dirs=[str(config_dir)])

    assert data["mode"] == "Contest"
    assert source == str(canonical)


def test_load_local_config_uses_bundled_baseline_when_profiles_are_ambiguous(tmp_path):
    config_dir = tmp_path / "boot" / "gallos" / "config"
    config_dir.mkdir(parents=True)
    baseline = config_dir / "baseline" / "baseline.gallos.toml"
    baseline.parent.mkdir()
    baseline.write_text('mode = "Default"\n', encoding="utf-8")
    (config_dir / "day-one.gallos.toml").write_text('mode = "Event"\n', encoding="utf-8")
    (config_dir / "day-two.gallos.toml").write_text('mode = "Contest"\n', encoding="utf-8")

    data, source = load_local_config(search_dirs=[str(config_dir)])

    assert data["mode"] == "Default"
    assert source == str(baseline)


def test_load_local_config_multiple_profiles_ambiguity_returns_none(tmp_path):
    config_dir = tmp_path / "boot" / "gallos"
    config_dir.mkdir(parents=True)
    (config_dir / "p1.gallos.toml").write_text('mode = "Contest"\n', encoding="utf-8")
    (config_dir / "p2.gallos.toml").write_text('mode = "Event"\n', encoding="utf-8")

    data, source = load_local_config(search_dirs=[str(config_dir)])
    assert data is None
    assert source == ""


def test_load_machine_config_auto_discovers_unique_profile(tmp_path):
    config_dir = tmp_path / "boot" / "gallos"
    config_dir.mkdir(parents=True)
    target_file = config_dir / "pc-42.machine.toml"
    target_file.write_text('hostname = "pc-42"\n', encoding="utf-8")

    data = load_machine_config(search_dirs=[str(config_dir)])
    assert data.get("hostname") == "pc-42"
