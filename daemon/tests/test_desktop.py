"""Unit tests for gallosd desktop integration module."""

from unittest.mock import mock_open, patch

from daemon.src.desktop import export_waybar_state, send_desktop_notification, update_wallpaper


def test_export_waybar_state_standby():
    m = mock_open()
    with (
        patch("daemon.src.desktop.os.makedirs"),
        patch("builtins.open", m),
        patch("daemon.src.desktop.json.dump") as mock_json_dump,
        patch("daemon.src.desktop.os.chmod"),
    ):
        export_waybar_state("Default", remaining_seconds=0)
        assert mock_json_dump.called
        payload = mock_json_dump.call_args[0][0]
        assert payload["mode"] == "Default"
        assert payload["badge"] == "MODE: DEFAULT"
        assert payload["time_str"] == "Standby"
        assert "⏳" not in payload["time_str"]
        assert payload["remaining_sec"] == 0


def test_export_waybar_state_active_countdown():
    m = mock_open()
    with (
        patch("daemon.src.desktop.os.makedirs"),
        patch("builtins.open", m),
        patch("daemon.src.desktop.json.dump") as mock_json_dump,
        patch("daemon.src.desktop.os.chmod"),
    ):
        export_waybar_state("Contest", remaining_seconds=3665)
        assert mock_json_dump.called
        payload = mock_json_dump.call_args[0][0]
        assert payload["mode"] == "Contest"
        assert payload["badge"] == "MODE: CONTEST"
        assert payload["time_str"] == "01:01:05"
        assert "⏳" not in payload["time_str"]
        assert payload["remaining_sec"] == 3665


def test_send_desktop_notification():
    with patch("subprocess.run") as mock_run:
        send_desktop_notification("Contest Alert", "Contest is starting soon", urgency="critical")
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "notify-send" in cmd[4]
        assert "Contest Alert" in cmd[4]


def test_local_wallpaper_is_published_as_literal_data(tmp_path):
    import json

    from daemon.src import desktop

    asset = tmp_path / "background ' $(touch injected).png"
    asset.write_bytes(b"image")
    state = tmp_path / "wallpaper.json"
    with patch.object(desktop, "WALLPAPER_STATE", state, create=True):
        update_wallpaper("Contest", str(asset))
    assert json.loads(state.read_text())["path"] == str(asset)
    assert not (tmp_path / "injected").exists()


def test_missing_wallpaper_publishes_bundled_fallback(tmp_path, capsys):
    import json

    from daemon.src import desktop

    state = tmp_path / "wallpaper.json"
    with patch.object(desktop, "WALLPAPER_STATE", state, create=True):
        update_wallpaper("Contest", str(tmp_path / "missing.png"))
    assert json.loads(state.read_text())["path"] == "/usr/share/backgrounds/gallos/contest.png"
    assert "fallback" in capsys.readouterr().err.lower()
