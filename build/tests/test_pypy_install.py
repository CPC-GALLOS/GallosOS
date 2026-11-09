"""Reject corrupted contestant runtimes before extracting or executing them."""

import os
import subprocess
from pathlib import Path


def test_corrupt_pypy_archive_does_not_replace_system_python(tmp_path):
    root = tmp_path / "root"
    (root / "usr/bin").mkdir(parents=True)
    system = root / "usr/bin/python3"
    system.write_text("system interpreter")
    tools = tmp_path / "bin"
    tools.mkdir()
    curl = tools / "curl"
    curl.write_text(
        '#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\nif [ "$1" = "-o" ]; then shift; printf corrupt > "$1"; exit 0; fi\nshift\ndone\nexit 1\n'
    )
    curl.chmod(0o755)
    script = Path(__file__).resolve().parents[1] / "scripts/install-contest-pypy.sh"
    result = subprocess.run(
        ["bash", str(script), str(root)],
        env={**os.environ, "PATH": f"{tools}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "checksum" in (result.stdout + result.stderr).lower()
    assert system.read_text() == "system interpreter"
    assert not (root / "usr/local/bin/pypy3").exists()
