#!/usr/bin/env bash
# Stage 5a: Squash & Stitch, squashfs half (docs/BUILD_SYSTEM.md §3 Stage 5 /
# ROADMAP.md Phase 1 "SquashFS Packaging Scripts").
#
# Copies the kernel + initrd out to the ISO staging tree's /casper/ (grub
# loads these directly — standard casper ISO layout), then compresses the
# rest of $ROOTFS into filesystem.squashfs, excluding /boot (duplicated onto
# the ISO directly) and the *contents* of /proc, /sys, /dev, /tmp, /run
# (kernel/systemd-populated at boot; also defends against mksquashfs
# otherwise walking whatever happens to still be mounted there from the
# chroot stages — verified this happens in practice, not just theoretical).
#
# Deliberately excludes only contents (tmp/*), not the directories
# themselves: excluding the bare directory entirely (as an earlier version
# of this script did with plain `-e tmp`) meant chroot'd /tmp didn't exist
# at boot at all, breaking casper's post-hooks debconf cleanup (`mktemp -dt
# debconf.XXXXXX` failed with "No such file or directory") — which is what
# actually killed PID 1, not any casper-bottom hook (verified interactively
# via QEMU + break=casper-bottom).
set -euo pipefail

ROOTFS="$1"
STAGING="$2"   # ISO staging root, e.g. build/output/staging

mkdir -p "$STAGING/casper"

vmlinuz="$(find "$ROOTFS/boot" -maxdepth 1 -name 'vmlinuz-*' | sort -V | tail -1)"
kernel_version="${vmlinuz##*/vmlinuz-}"
initrd="$ROOTFS/boot/initrd.img-$kernel_version"
if [[ -z "$vmlinuz" || ! -f "$initrd" ]]; then
    echo "build-squashfs.sh: no kernel/initrd found under $ROOTFS/boot" >&2
    exit 1
fi
if ! sbverify --cert /usr/share/grub/canonical-uefi-ca.crt "$vmlinuz" >/dev/null 2>&1; then
    echo "build-squashfs.sh: selected kernel lacks a valid Canonical signature: $vmlinuz" >&2
    exit 1
fi
cp "$vmlinuz" "$STAGING/casper/vmlinuz"
cp "$initrd" "$STAGING/casper/initrd"

echo "Compressing $ROOTFS -> $STAGING/casper/filesystem.squashfs (zstd)..."
rm -f "$STAGING/casper/filesystem.squashfs"
mksquashfs "$ROOTFS" "$STAGING/casper/filesystem.squashfs" \
    -comp zstd -wildcards \
    -e "boot/*" -e "proc/*" -e "sys/*" -e "dev/*" -e "tmp/*" -e "run/*" \
    -noappend

du -sx --block-size=1 "$ROOTFS" | cut -f1 > "$STAGING/casper/filesystem.size"

echo "Stage 5a complete: $STAGING/casper/"
