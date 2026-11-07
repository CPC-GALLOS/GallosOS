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


def test_update_wallpaper():
    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
    ):
        update_wallpaper("Contest")
        assert mock_run.called
        assert mock_popen.called
        popen_args = mock_popen.call_args[0][0]
        assert "contest.png" in popen_args[4]


def test_send_desktop_notification():
    with patch("subprocess.run") as mock_run:
        send_desktop_notification("Contest Alert", "Contest is starting soon", urgency="critical")
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "notify-send" in cmd[4]
        assert "Contest Alert" in cmd[4]
