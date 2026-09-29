#!/usr/bin/env bash
# Run after the ISO pipeline, inside gallos-builder with the generated rootfs.
set -euo pipefail

ROOTFS="${1:?rootfs path required}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=build/scripts/lib-chroot.sh
source "$SCRIPT_DIR/lib-chroot.sh"

chroot_mount "$ROOTFS"
trap 'rm -f "$ROOTFS/tmp/gallos-verify-toolchains.sh"; chroot_umount "$ROOTFS"' EXIT
install -m 0755 "$SCRIPT_DIR/verify-toolchains.sh" "$ROOTFS/tmp/gallos-verify-toolchains.sh"
chroot "$ROOTFS" /bin/bash /tmp/gallos-verify-toolchains.sh
