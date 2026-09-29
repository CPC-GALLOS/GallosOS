#!/usr/bin/env bash
# Assemble a BIOS/UEFI hybrid ISO with Ubuntu's signed EFI boot chain.
set -euo pipefail

STAGING="${1:?staging directory required}"
OUT_ISO="${2:?ISO output path required}"
VOLID="GALLOS_BOOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SHIM=/usr/lib/shim/shimx64.efi.signed.latest
GRUB_SIGNED=/usr/lib/grub/x86_64-efi-signed/grubx64.efi.signed
MOK=/usr/lib/shim/mmx64.efi
BIOS_MBR=/usr/lib/grub/i386-pc/boot_hybrid.img

for artifact in "$SHIM" "$GRUB_SIGNED" "$MOK" "$BIOS_MBR" \
    "$STAGING/casper/vmlinuz" "$STAGING/casper/initrd"; do
    if [[ ! -s "$artifact" ]]; then
        echo "build-iso.sh: required boot artifact missing: $artifact" >&2
        exit 1
    fi
done
if ! sbverify --list "$SHIM" >/dev/null 2>&1; then
    echo "build-iso.sh: unsigned shim artifact: $SHIM" >&2
    exit 1
fi
for signed in "$GRUB_SIGNED" "$MOK" "$STAGING/casper/vmlinuz"; do
    if ! sbverify --cert /usr/share/grub/canonical-uefi-ca.crt "$signed" >/dev/null 2>&1; then
        echo "build-iso.sh: invalid Canonical signature: $signed" >&2
        exit 1
    fi
done

mkdir -p "$STAGING/boot/grub" "$(dirname "$OUT_ISO")"
DEFAULT_DIRECTIVES="$REPO_ROOT/examples/neutral.gallos.toml"
DIRECTIVES_PROFILE="${3:-}"
REMOTE_POLICY_URL="${4:-}"
if [[ -z "$DIRECTIVES_PROFILE" ]]; then
    DIRECTIVES_SRC="$DEFAULT_DIRECTIVES"
elif [[ "$DIRECTIVES_PROFILE" = /* ]]; then
    DIRECTIVES_SRC="$DIRECTIVES_PROFILE"
else
    DIRECTIVES_SRC="$REPO_ROOT/$DIRECTIVES_PROFILE"
fi
if [[ ! -f "$DIRECTIVES_SRC" ]]; then
    echo "build-iso.sh: runtime directives profile not found: $DIRECTIVES_SRC" >&2
    exit 1
fi
# shellcheck source=build/scripts/lib-directives.sh
source "$SCRIPT_DIR/lib-directives.sh"
copy_directives_profile "$DIRECTIVES_SRC" "$STAGING"
copy_remote_policy_url "$REMOTE_POLICY_URL" "$STAGING"
cat > "$STAGING/boot/grub/grub.cfg" <<EOF
serial --unit=0 --speed=115200
terminal_input serial console
terminal_output serial console
set default=0
set timeout=5

menuentry "GallosOS Live" {
    search --no-floppy --set=root --label $VOLID
    linux /casper/vmlinuz boot=casper hostname=GallosOS console=ttyS0,115200n8 ipv6.disable=1
    initrd /casper/initrd
}
menuentry "GallosOS Live (toram)" {
    search --no-floppy --set=root --label $VOLID
    linux /casper/vmlinuz boot=casper hostname=GallosOS console=ttyS0,115200n8 ipv6.disable=1 toram
    initrd /casper/initrd
}
EOF

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# Ubuntu's signed GRUB embeds /EFI/ubuntu as its config prefix. This small
# config selects the ISO filesystem before loading the shared GRUB menu.
cat > "$WORK_DIR/efi-grub.cfg" <<EOF
serial --unit=0 --speed=115200
terminal_input serial console
terminal_output serial console
search --no-floppy --set=root --label $VOLID
configfile /boot/grub/grub.cfg
EOF
# On optical boot, Ubuntu's signed GRUB reports fw_path on the ISO (cd0),
# while USB firmware loads it from the appended FAT ESP. Provide both paths.
mkdir -p "$STAGING/EFI/BOOT" "$STAGING/EFI/ubuntu"
cp "$WORK_DIR/efi-grub.cfg" "$STAGING/EFI/ubuntu/grub.cfg"
cp "$WORK_DIR/efi-grub.cfg" "$STAGING/EFI/BOOT/grub.cfg"
cp "$SHIM" "$STAGING/EFI/BOOT/BOOTX64.EFI"
cp "$GRUB_SIGNED" "$STAGING/EFI/BOOT/grubx64.efi"
cp "$MOK" "$STAGING/EFI/BOOT/mmx64.efi"
ESP_IMAGE="$WORK_DIR/efi.img"
truncate -s 16M "$ESP_IMAGE"
mkfs.vfat -F 16 -n GALLOS_EFI "$ESP_IMAGE" >/dev/null
mmd -i "$ESP_IMAGE" ::/EFI ::/EFI/BOOT ::/EFI/ubuntu
mcopy -i "$ESP_IMAGE" "$SHIM" ::/EFI/BOOT/BOOTX64.EFI
mcopy -i "$ESP_IMAGE" "$GRUB_SIGNED" ::/EFI/BOOT/grubx64.efi
mcopy -i "$ESP_IMAGE" "$MOK" ::/EFI/BOOT/mmx64.efi
mcopy -i "$ESP_IMAGE" "$WORK_DIR/efi-grub.cfg" ::/EFI/ubuntu/grub.cfg
mcopy -i "$ESP_IMAGE" "$WORK_DIR/efi-grub.cfg" ::/EFI/BOOT/grub.cfg

# Keep the BIOS core below GRUB's boot-sector size limit. Its embedded
# configuration searches for the shared menu on the ISO filesystem.
cp "$WORK_DIR/efi-grub.cfg" "$WORK_DIR/bios-grub.cfg"
grub-mkimage -O i386-pc-eltorito -C xz -o "$STAGING/boot/grub/bios.img" \
    -p /boot/grub -c "$WORK_DIR/bios-grub.cfg" \
    biosdisk iso9660 normal search search_label linux part_msdos part_gpt configfile serial terminal

# casper-md5check expects a manifest at the ISO root. Generate it after all
# staged files are final; the manifest itself cannot include its own digest.
(
    cd "$STAGING"
    find . -type f ! -name md5sum.txt ! -path './boot/grub/bios.img' -print0 \
        | LC_ALL=C sort -z | xargs -0 md5sum \
        > "$WORK_DIR/md5sum.txt"
)
cp "$WORK_DIR/md5sum.txt" "$STAGING/md5sum.txt"

echo "Assembling signed BIOS/UEFI hybrid ISO -> $OUT_ISO..."
# A prior migration may leave the canonical output path as a symlink to an
# older image. Remove only the link; never follow it or overwrite its target.
if [[ -L "$OUT_ISO" ]]; then
    rm -- "$OUT_ISO"
fi
xorriso -as mkisofs -R -J -iso-level 3 -volid "$VOLID" \
    -b boot/grub/bios.img -no-emul-boot -boot-load-size 4 -boot-info-table \
    --grub2-mbr "$BIOS_MBR" -partition_offset 16 \
    -eltorito-alt-boot -e --interval:appended_partition_2:all:: -no-emul-boot \
    -append_partition 2 0xef "$ESP_IMAGE" \
    -o "$OUT_ISO" "$STAGING"

dpkg-query -W -f='${Package} ${Version}\n' shim-signed grub-efi-amd64-signed \
    > "${OUT_ISO%.iso}.boot-packages.txt"
(
    cd "$(dirname "$OUT_ISO")"
    iso_name="$(basename "$OUT_ISO")"
    sha256sum "$iso_name" > "${iso_name%.iso}.sha256"
)
echo "Stage 5b complete: $OUT_ISO"
