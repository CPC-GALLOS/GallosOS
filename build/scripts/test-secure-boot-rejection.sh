#!/usr/bin/env bash
# Confirm enforced Secure Boot rejects a changed kernel from the same ISO.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${1:-}"
if [[ -z "$ISO" ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    for candidate in "$REPO_ROOT/build/output/gallosos-universal-amd64.iso" \
                     "$REPO_ROOT/build/output/gallos-os-amd64.iso"; do
        if [[ -f "$candidate" ]]; then
            ISO="$candidate"
            break
        fi
    done
    ISO="${ISO:-${1:?Usage: $0 /path/to/gallosos.iso}}"
fi
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

xorriso -indev "$ISO" -osirrox on \
    -extract /casper/vmlinuz "$WORK_DIR/vmlinuz" >/dev/null 2>&1
python3 - "$WORK_DIR/vmlinuz" "$WORK_DIR/tampered-vmlinuz" <<'PY'
from pathlib import Path
import sys

image = bytearray(Path(sys.argv[1]).read_bytes())
if len(image) < 100_001:
    raise SystemExit("kernel image is too small for this test")
image[100_000] ^= 1
Path(sys.argv[2]).write_bytes(image)
PY

xorriso -indev "$ISO" -outdev "$WORK_DIR/tampered.iso" \
    -map "$WORK_DIR/tampered-vmlinuz" /casper/vmlinuz \
    -boot_image any replay -commit >/dev/null 2>&1

bash "$SCRIPT_DIR/test-iso-qemu.sh" --expect-rejection \
    --iso "$WORK_DIR/tampered.iso"
