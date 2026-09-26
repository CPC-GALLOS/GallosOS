"""Smoke harness selects the GRUB toram entry and waits for Linux boot."""

import subprocess
import sys


def test_watcher_selects_toram_entry(tmp_path):
    fake_vm = tmp_path / "fake_vm.py"
    fake_vm.write_text(
        "import sys\n"
        "print('GallosOS Live (toram)', flush=True)\n"
        "keys = sys.stdin.buffer.read(4)\n"
        "if keys == b'\\x1b[B\\r':\n"
        "    print('secureboot: Secure boot enabled', flush=True)\n"
        "    print('Reached target multi-user.target - Multi-User System.', flush=True)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "build/scripts/watch-qemu-boot.py",
            "--toram",
            "1",
            "--secure-boot",
            "1",
            "--expect-rejection",
            "0",
            "--",
            sys.executable,
            str(fake_vm),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_watcher_accepts_rejected_tampered_kernel(tmp_path):
    fake_vm = tmp_path / "fake_rejection.py"
    fake_vm.write_text("print('error: bad shim signature.', flush=True)\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "build/scripts/watch-qemu-boot.py",
            "--toram",
            "0",
            "--secure-boot",
            "1",
            "--expect-rejection",
            "1",
            "--",
            sys.executable,
            str(fake_vm),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_watcher_accepts_colored_systemd_target(tmp_path):
    fake_vm = tmp_path / "fake_colored_boot.py"
    fake_vm.write_text(
        "print('[  OK  ] Reached target \\x1b[0;1;39m"
        "multi-user.target\\x1b[0m - Multi-User System.', flush=True)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "build/scripts/watch-qemu-boot.py",
            "--toram",
            "0",
            "--secure-boot",
            "0",
            "--expect-rejection",
            "0",
            "--",
            sys.executable,
            str(fake_vm),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
