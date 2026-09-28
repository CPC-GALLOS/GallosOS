#!/usr/bin/env python3
"""Watch the QEMU serial console for a real multi-user boot."""

import os
import select
import subprocess
import sys
import time


def parse_options() -> tuple[bool, bool, bool, list[str]] | None:
    if (
        len(sys.argv) < 9
        or sys.argv[1] != "--toram"
        or sys.argv[3] != "--secure-boot"
        or sys.argv[5] != "--expect-rejection"
        or sys.argv[7] != "--"
    ):
        print(
            "usage: watch-qemu-boot.py --toram 0|1 --secure-boot 0|1 "
            "--expect-rejection 0|1 -- command...",
            file=sys.stderr,
        )
        return None
    return sys.argv[2] == "1", sys.argv[4] == "1", sys.argv[6] == "1", sys.argv[8:]


def watch(
    process: subprocess.Popen[bytes], select_toram: bool, secure_boot: bool
) -> tuple[bool, bool]:
    assert process.stdout is not None
    assert process.stdin is not None
    # Software emulation on hosts without /dev/kvm can take several minutes.
    deadline = time.monotonic() + 420
    recent = bytearray()
    selected = False
    enforcement_seen = False
    while time.monotonic() < deadline:
        ready, _, _ = select.select([process.stdout], [], [], 1)
        if ready:
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            recent.extend(chunk)
            if len(recent) > 16384:
                del recent[:-8192]
            if select_toram and not selected and b"GallosOS Live (toram)" in recent:
                process.stdin.write(b"\x1b[B\r")
                process.stdin.flush()
                selected = True
            if b"secureboot: Secure boot enabled" in recent:
                enforcement_seen = True
            if b"error: bad shim signature" in recent and b"Linux version" not in recent:
                return False, True
            if (
                b"Reached target" in recent
                and b"multi-user.target" in recent
                and b"Multi-User System" in recent
            ) and (not secure_boot or enforcement_seen):
                return True, False
        if process.poll() is not None:
            break
    return False, False


def main() -> int:
    options = parse_options()
    if options is None:
        return 2
    select_toram, secure_boot, expect_rejection, command = options
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        booted, rejected = watch(process, select_toram, secure_boot)
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    if expect_rejection:
        if not rejected:
            print("QEMU did not reject the tampered kernel", file=sys.stderr)
        return 0 if rejected else 1
    if not booted:
        print(
            "QEMU did not reach Multi-User System with the requested boot policy",
            file=sys.stderr,
        )
    return 0 if booted else 1


if __name__ == "__main__":
    raise SystemExit(main())
