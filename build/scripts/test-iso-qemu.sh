#!/usr/bin/env bash
# Boot the actual ISO firmware path in QEMU, optionally enforcing Secure Boot.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ISO=""
UEFI=0
SECURE_BOOT=0
TORAM=0
SMOKE=0
HEADLESS=0
EXPECT_REJECTION=0
USB_IMAGE=""
MEM=4096
CPUS=2

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uefi) UEFI=1 ;;
        --secure-boot) UEFI=1; SECURE_BOOT=1 ;;
        --toram) TORAM=1; SMOKE=1; HEADLESS=1 ;;
        --smoke) SMOKE=1; HEADLESS=1 ;;
        --headless) HEADLESS=1 ;;
        --expect-rejection) UEFI=1; SECURE_BOOT=1; SMOKE=1; HEADLESS=1; EXPECT_REJECTION=1 ;;
        --iso) shift; ISO="${1:?--iso needs a path}" ;;
        --usb-image) shift; USB_IMAGE="${1:?--usb-image needs a path}" ;;
        --mem) shift; MEM="${1:?--mem needs a value}" ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

if [[ -z "$ISO" ]]; then
    for candidate in "$REPO_ROOT/build/output/gallosos-universal-amd64.iso" \
                     "$REPO_ROOT/build/output/gallos-os-amd64.iso"; do
        if [[ -f "$candidate" ]]; then
            ISO="$candidate"
            break
        fi
    done
    ISO="${ISO:-$REPO_ROOT/build/output/gallosos-universal-amd64.iso}"
fi

if [[ ! -f "$ISO" ]]; then
    echo "ISO not found: $ISO" >&2
    exit 1
fi
if [[ -n "$USB_IMAGE" && ! -f "$USB_IMAGE" ]]; then
    echo "USB image not found: $USB_IMAGE" >&2
    exit 1
fi

QEMU_ARGS=(-m "$MEM" -smp "$CPUS" -netdev "user,id=net0"
    -device "virtio-net-pci,netdev=net0" -cdrom "$ISO" -boot d)
if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    QEMU_ARGS+=(-enable-kvm -cpu "host,-vmx")
else
    QEMU_ARGS+=(-accel tcg -cpu qemu64)
fi
if [[ $HEADLESS -eq 1 ]]; then
    QEMU_ARGS+=(-nographic)
else
    QEMU_ARGS+=(-vga virtio -display gtk -serial mon:stdio)
fi
if [[ -n "$USB_IMAGE" ]]; then
    QEMU_ARGS+=(-drive "if=none,id=gallosusb,format=raw,file=$USB_IMAGE"
        -device usb-ehci -device "usb-storage,drive=gallosusb")
fi

if [[ $SECURE_BOOT -eq 1 ]]; then
    CODE=""
    VARS=""
    for pair in \
        /usr/share/edk2/ovmf/OVMF_CODE.secboot.fd:/usr/share/edk2/ovmf/OVMF_VARS.secboot.fd \
        /usr/share/OVMF/OVMF_CODE_4M.secboot.fd:/usr/share/OVMF/OVMF_VARS_4M.ms.fd \
        /usr/share/OVMF/OVMF_CODE.secboot.fd:/usr/share/OVMF/OVMF_VARS.ms.fd; do
        candidate_code="${pair%%:*}"
        candidate_vars="${pair#*:}"
        if [[ -s "$candidate_code" && -s "$candidate_vars" ]]; then
            CODE="$candidate_code"
            VARS="$candidate_vars"
            break
        fi
    done
    if [[ ! -s "$CODE" || ! -s "$VARS" ]]; then
        echo "Secure Boot OVMF CODE/VARS with enrolled Microsoft keys are missing" >&2
        exit 1
    fi
    OVMF_DIR="$(mktemp -d)"
    trap 'rm -rf "$OVMF_DIR"' EXIT
    cp "$VARS" "$OVMF_DIR/vars.fd"
    QEMU_ARGS+=(-machine "q35,smm=on"
        -global "driver=cfi.pflash01,property=secure,value=on"
        -drive "if=pflash,format=raw,unit=0,readonly=on,file=$CODE"
        -drive "if=pflash,format=raw,unit=1,file=$OVMF_DIR/vars.fd")
elif [[ $UEFI -eq 1 ]]; then
    CODE=""
    VARS=""
    for pair in \
        /usr/share/edk2/ovmf/OVMF_CODE.fd:/usr/share/edk2/ovmf/OVMF_VARS.fd \
        /usr/share/OVMF/OVMF_CODE_4M.fd:/usr/share/OVMF/OVMF_VARS_4M.fd \
        /usr/share/OVMF/OVMF_CODE.fd:/usr/share/OVMF/OVMF_VARS.fd; do
        candidate_code="${pair%%:*}"
        candidate_vars="${pair#*:}"
        if [[ -s "$candidate_code" && -s "$candidate_vars" ]]; then
            CODE="$candidate_code"
            VARS="$candidate_vars"
            break
        fi
    done
    if [[ ! -s "$CODE" || ! -s "$VARS" ]]; then
        echo "OVMF CODE/VARS firmware pair not found" >&2
        exit 1
    fi
    OVMF_DIR="$(mktemp -d)"
    trap 'rm -rf "$OVMF_DIR"' EXIT
    cp "$VARS" "$OVMF_DIR/vars.fd"
    QEMU_ARGS+=(-machine q35
        -drive "if=pflash,format=raw,unit=0,readonly=on,file=$CODE"
        -drive "if=pflash,format=raw,unit=1,file=$OVMF_DIR/vars.fd")
fi

echo "Booting $ISO (UEFI=$UEFI, Secure Boot=$SECURE_BOOT, toram=$TORAM)"
if [[ $SMOKE -eq 1 ]]; then
    python3 "$SCRIPT_DIR/watch-qemu-boot.py" --toram "$TORAM" \
        --secure-boot "$SECURE_BOOT" --expect-rejection "$EXPECT_REJECTION" -- \
        qemu-system-x86_64 "${QEMU_ARGS[@]}"
else
    qemu-system-x86_64 "${QEMU_ARGS[@]}"
fi
