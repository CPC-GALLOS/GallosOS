#!/usr/bin/env bash
# ICPC's PyPy is separate from /usr/bin/python3 used by the operating system.
# Sources: https://docs.icpc.global/worldfinals-programming-environment/
#          https://pypy.org/checksums.html
set -euo pipefail
ROOTFS="${1:?usage: install-contest-pypy.sh ROOTFS}"
asset=pypy3.9-v7.3.15-linux64.tar.bz2
digest=f062be307200bde434817e1620cebc13f563d6ab25309442c5f4d0f0d68f0912
install -d "$ROOTFS/tmp" "$ROOTFS/opt" "$ROOTFS/usr/local/bin" "$ROOTFS/usr/share/gallos"
archive="$(mktemp "$ROOTFS/tmp/pypy-XXXXXXXX.tar.bz2")"
trap 'rm -f "$archive"' EXIT
curl -fsSL "https://downloads.python.org/pypy/$asset" -o "$archive"
printf '%s  %s\n' "$digest" "$archive" | sha256sum --check
# Preserve the entire distribution: the interpreter needs its adjacent libraries.
python3 - "$archive" "$ROOTFS/opt" <<'PYTHON'
import sys
import tarfile

with tarfile.open(sys.argv[1], "r:bz2") as distribution:
    distribution.extractall(sys.argv[2], filter="data")
PYTHON
ln -sfn /opt/pypy3.9-v7.3.15-linux64/bin/pypy3 "$ROOTFS/usr/local/bin/pypy3"
printf 'pypy3-icpc\tPyPy 7.3.15 / Python 3.9.18\t%s\n' "$digest" \
    > "$ROOTFS/usr/share/gallos/contest-python.tsv"
