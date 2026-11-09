"""Apply daemon-published wallpaper state inside the contestant Wayland session."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


class WallpaperSession:
    """Own the swaybg child for one compositor session."""

    def __init__(self, state: Path = Path("/run/gallos/wallpaper.json")) -> None:
        self.state = state
        self.path = ""
        self.requested_path = ""
        self.process: subprocess.Popen | None = None

    def refresh(self) -> None:
        try:
            payload = json.loads(self.state.read_text(encoding="utf-8"))
            requested = payload["path"]
            path = requested
            if not os.path.isfile(path) or not os.access(path, os.R_OK):
                print(f"[wallpaper] Cannot read {path!r}; using fallback", file=sys.stderr)
                path = payload["fallback"]
            if requested == self.requested_path and self.process is not None:
                if self.process.poll() is None:
                    return
                print(
                    f"[wallpaper] Renderer exited for {self.path!r}; using fallback",
                    file=sys.stderr,
                )
                path = payload["fallback"]
            if self.process is not None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.process = subprocess.Popen(["swaybg", "-i", path, "-m", "fill"])
            self.path = path
            self.requested_path = requested
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"[wallpaper] {exc}", file=sys.stderr)


def main() -> None:
    session = WallpaperSession()
    while True:
        session.refresh()
        time.sleep(1)


if __name__ == "__main__":
    main()
