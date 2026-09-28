#!/usr/bin/env bash
# Stage 1: Base Bootstrap (docs/BUILD_SYSTEM.md §3).
#
# Default: runs debootstrap against a configurable apt mirror
# (build.toml [build].apt_mirror — "auto"/unset tries an ordered fallback
# list, or an explicit URL). This is the default because it's where real
# mirror flexibility exists — see lib-mirrors.sh's header for why.
#
# Alternate: build.toml [build].bootstrap_method = "tarball" imports the
# explicitly versioned Canonical Ubuntu Base snapshot from .cache/base-images/
# or its official release archive, with its checksum verified before use.
set -euo pipefail

CONFIG="$1"
ROOTFS="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="/repo/.cache/base-images"
SUITE="noble" # Ubuntu 24.04 LTS codename

# shellcheck source=build/scripts/lib-mirrors.sh
source "$SCRIPT_DIR/lib-mirrors.sh"

base_os="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" build.base_os)"
if [[ "$base_os" != "ubuntu-24.04-minimal" ]]; then
    echo "01-bootstrap.sh: only ubuntu-24.04-minimal is wired up so far (got '$base_os')" >&2
    exit 1
fi

method="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" build.bootstrap_method)"
method="${method:-debootstrap}"

rm -rf "$ROOTFS"
mkdir -p "$ROOTFS"

case "$method" in
tarball)
    mkdir -p "$CACHE_DIR"
    base_version="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" build.ubuntu_base_version)"
    if [[ -z "$base_version" ]]; then
        echo "01-bootstrap.sh: tarball bootstrap requires build.ubuntu_base_version (for example, 24.04.5)" >&2
        exit 1
    fi
    if [[ ! "$base_version" =~ ^24\.04\.[0-9]+$ ]]; then
        echo "01-bootstrap.sh: unsupported Ubuntu Base version '$base_version' (expected 24.04.x)" >&2
        exit 1
    fi

    tarball_name="ubuntu-base-${base_version}-base-amd64.tar.gz"
    sums_name="ubuntu-base-${base_version}-SHA256SUMS"
    tarball="$CACHE_DIR/$tarball_name"
    sums_file="$CACHE_DIR/$sums_name"
    if [[ ! -s "$tarball" ]]; then
        echo "01-bootstrap.sh: Downloading official Ubuntu Base ${base_version}..."
        curl -fsSL -o "$tarball" \
            "https://cdimage.ubuntu.com/cdimage/ubuntu-base/releases/24.04/release/$tarball_name"
    fi
    if [[ ! -s "$sums_file" ]]; then
        curl -fsSL -o "$sums_file" \
            "https://cdimage.ubuntu.com/cdimage/ubuntu-base/releases/24.04/release/SHA256SUMS"
    fi

    echo "Verifying $(basename "$tarball") against $(basename "$sums_file")..."
    expected="$(awk -v file="$tarball_name" '$2 == file { print $1; exit }' "$sums_file")"
    actual="$(sha256sum "$tarball" | awk '{print $1}')"
    if [[ -z "$expected" || "$expected" != "$actual" ]]; then
        echo "01-bootstrap.sh: SHA256 mismatch for $tarball" >&2
        echo "  expected: ${expected:-missing checksum entry}" >&2
        echo "  actual:   $actual" >&2
        exit 1
    fi

    echo "Extracting $(basename "$tarball") into $ROOTFS..."
    tar -xpf "$tarball" -C "$ROOTFS"
    ;;
debootstrap)
    configured_mirror="$(python3 "$SCRIPT_DIR/tomlget.py" "$CONFIG" build.apt_mirror)"
    if ! mirror="$(pick_apt_mirror "$SUITE" "$configured_mirror")"; then
        echo "01-bootstrap.sh: could not resolve an apt mirror" >&2
        exit 1
    fi
    echo "Bootstrapping $SUITE via debootstrap from $mirror..."
    debootstrap --arch=amd64 "$SUITE" "$ROOTFS" "$mirror"
    # Expect: "W: Could not create /dev/ptmx, falling back to symlink. This
    # chroot will require /dev/pts mounted with ptmxmode=666" — debootstrap
    # tries to mknod a few device nodes in its second stage; rootless
    # Podman denies CAP_MKNOD even under --privileged (same restriction
    # lib-chroot.sh's chroot_mount() works around for Stage 2/3 via
    # `mount --rbind` instead of mknod — see its header comment). Benign
    # here: chroot_mount()'s --rbind pulls in the container's own /dev/pts,
    # which already carries ptmxmode=666, satisfying the symlink's
    # requirement before anything in Stage 2 needs a working pty.

    # debootstrap only writes a single "main"-component, no-pockets line
    # (deb $mirror $SUITE main) — no restricted/universe/multiverse, no
    # -updates/-backports, and critically no -security (verified: this is
    # a real gap versus the ubuntu-base tarball path, whose Canonical-
    # shipped sources.list pulls all of these — confirmed against this
    # session's own earlier apt-get update logs, which fetched noble-
    # security separately from security.ubuntu.com). Match that here:
    # security always comes from security.ubuntu.com regardless of which
    # general mirror was chosen (community mirrors don't reliably mirror
    # the security pocket promptly) — standard Ubuntu/Debian convention.
    printf "deb %s %s main restricted universe multiverse\n" "${mirror%/}" "$SUITE" > "$ROOTFS/etc/apt/sources.list"
    printf "deb %s %s-updates main restricted universe multiverse\n" "${mirror%/}" "$SUITE" >> "$ROOTFS/etc/apt/sources.list"
    printf "deb %s %s-backports main restricted universe multiverse\n" "${mirror%/}" "$SUITE" >> "$ROOTFS/etc/apt/sources.list"
    printf "deb http://security.ubuntu.com/ubuntu %s-security main restricted universe multiverse\n" "$SUITE" >> "$ROOTFS/etc/apt/sources.list"
    ;;
*)
    echo "01-bootstrap.sh: unknown build.bootstrap_method '$method' (expected debootstrap or tarball)" >&2
    exit 1
    ;;
esac

# Populate the pseudo-filesystems chroot needs (mounted per-stage by
# 02-provision.sh / 03-optimize.sh, not held open here).
mkdir -p "$ROOTFS"/{dev,proc,sys}

# debootstrap's target does NOT create /tmp at all (unlike the ubuntu-base
# tarball, which ships it via base-files) — confirmed by hitting it: Stage
# 2's apt-get install failed with "unable to install new version of
# '/lib/modules/.../build': No such file or directory" because dpkg's own
# /tmp/apt-dpkg-install-* staging directory had nowhere to go. mkdir -p is
# a harmless no-op on the tarball path where /tmp already exists correctly.
mkdir -p "$ROOTFS/tmp" "$ROOTFS/var/tmp"
chmod 1777 "$ROOTFS/tmp" "$ROOTFS/var/tmp"

echo "Stage 1 complete: $ROOTFS"
