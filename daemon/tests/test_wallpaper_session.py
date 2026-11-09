"""The compositor-side consumer treats asset names as subprocess arguments."""

import json
from unittest.mock import MagicMock, patch


def test_new_session_consumes_published_wallpaper_and_updates(tmp_path):
    from daemon.src.wallpaper_session import WallpaperSession

    state = tmp_path / "wallpaper.json"
    asset = tmp_path / "wallpaper ' $(false).png"
    asset.write_bytes(b"png")
    state.write_text(json.dumps({"path": str(asset), "fallback": str(asset)}))
    running = MagicMock()
    running.poll.return_value = None
    with patch("subprocess.Popen", return_value=running) as spawn:
        session = WallpaperSession(state)
        session.refresh()
        assert spawn.call_args.args[0] == ["swaybg", "-i", str(asset), "-m", "fill"]
        session.refresh()
        assert spawn.call_count == 1


def test_failed_image_decoder_logs_and_uses_bundled_fallback(tmp_path, capsys):
    from daemon.src.wallpaper_session import WallpaperSession

    state = tmp_path / "wallpaper.json"
    asset = tmp_path / "readable-but-corrupt.png"
    fallback = tmp_path / "fallback.png"
    asset.write_bytes(b"invalid image")
    fallback.write_bytes(b"fixture")
    state.write_text(json.dumps({"path": str(asset), "fallback": str(fallback)}))
    failed = MagicMock()
    failed.poll.return_value = 1
    with patch("subprocess.Popen", side_effect=[failed, MagicMock()]) as spawn:
        session = WallpaperSession(state)
        session.refresh()
        session.refresh()
        assert spawn.call_args.args[0] == ["swaybg", "-i", str(fallback), "-m", "fill"]
        assert "fallback" in capsys.readouterr().err.lower()
