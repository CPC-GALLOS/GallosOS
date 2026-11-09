# Build and Image Verification Scripts

## Overview

These scripts turn a build manifest into an Ubuntu-based Live root filesystem
and hybrid ISO. Build stages run inside the `gallos-builder` container; QEMU
helpers run on a testing host with the required emulator and firmware installed.
The entry point is the [build Makefile](../Makefile), not a host invocation of
individual provisioning stages.

## Interface

| Entry point | Contract |
| :--- | :--- |
| [run-pipeline.sh](./run-pipeline.sh) | `CONFIG [DIRECTIVES_PROFILE] [REMOTE_POLICY_URL]`; runs the stages below in order and writes `/repo/build/output/gallosos-<profile>-amd64.iso`. Requires `GALLOS_GRUB_PASSWORD_HASH`. |
| [01-bootstrap.sh](./01-bootstrap.sh) | `CONFIG ROOTFS`; reads `build.base_os`, `build.bootstrap_method`, `build.apt_mirror`, and, for tarballs, `build.ubuntu_base_version`. |
| [02-provision.sh](./02-provision.sh) | `CONFIG ROOTFS`; reads `build.kernel` and `packages.preinstall_apt`, installs additional fixed packages, desktop configuration, Casper hooks, daemon sources, schema, and `gallosctl`. |
| [03-harden.sh](./03-harden.sh) | `CONFIG ROOTFS`; consumes `security.*` inputs for the initial firewall and USB configuration, installs runtime service units, and configures account and console restrictions. |
| [04-optimize.sh](./04-optimize.sh) | `CONFIG ROOTFS`; consumes `optimization.strip_man_pages`, `strip_docs`, `remove_apt_cache`, and `locales`. |
| [build-squashfs.sh](./build-squashfs.sh) | `ROOTFS STAGING`; writes `casper/vmlinuz`, `initrd`, `filesystem.squashfs`, and `filesystem.size`. |
| [build-iso.sh](./build-iso.sh) | `STAGING OUT_ISO [DIRECTIVES_PROFILE] [REMOTE_POLICY_URL]`; assembles BIOS/UEFI boot artifacts and emits the ISO, `.sha256`, and `.boot-packages.txt` files. |

The sourced libraries and Python reader provide the shared boundary:

- [lib-chroot.sh](./lib-chroot.sh): `chroot_mount ROOTFS` and
  `chroot_umount ROOTFS` manage pseudo-filesystems and resolver configuration.
- [lib-directives.sh](./lib-directives.sh): `copy_directives_profile SOURCE STAGING`
  stages `gallos/config/baseline/baseline.gallos.toml`;
  `copy_remote_policy_url URL STAGING` manages `gallos/config/remote-policy-url.txt`.
- [lib-grub.sh](./lib-grub.sh): `require_grub_password_hash HASH` validates the
  accepted GRUB PBKDF2-SHA512 syntax.
- [lib-mirrors.sh](./lib-mirrors.sh): `pick_apt_mirror SUITE CONFIGURED` prints a
  reachable mirror URL, using ordered fallbacks only for an empty or `auto` setting.
- [tomlget.py](./tomlget.py): `FILE SECTION.KEY` prints scalars, lowercase booleans,
  or one list element per line; an absent key produces no output and exits zero.

Image verification helpers are separate entry points:

- [test-iso-qemu.sh](./test-iso-qemu.sh) accepts `--iso PATH`, `--uefi`,
  `--secure-boot`, `--toram`, `--smoke`, `--headless`, `--expect-rejection`,
  `--usb-image PATH`, and `--mem MIB`. It selects KVM when accessible, otherwise TCG.
- [watch-qemu-boot.py](./watch-qemu-boot.py) accepts
  `--toram 0|1 --secure-boot 0|1 --expect-rejection 0|1 -- COMMAND...` and monitors
  serial output for the boot or rejection markers used by the QEMU wrapper.
- [test-secure-boot-rejection.sh](./test-secure-boot-rejection.sh) accepts an
  optional ISO path, creates a temporary kernel-tampered ISO, and invokes the
  QEMU rejection check.
- [make-test-usb-image.sh](./make-test-usb-image.sh) accepts an output image path
  and creates a synthetic `GALLOS_BOOT`/`event-data` disk with a dummy `.gsm`
  module. This is a QEMU fixture, not a flasher-produced deployment image.
- [verify-toolchains.sh](./verify-toolchains.sh) checks installed commands and
  compiles or runs small language samples inside a built rootfs or Live session.
  [verify-rootfs-toolchains.sh](./verify-rootfs-toolchains.sh) accepts `ROOTFS`
  and runs that check through the builder's chroot helpers.

## Invariants

- `run-pipeline.sh` validates the GRUB hash, an explicitly supplied directives
  file, and the optional HTTPS policy URL before bootstrap. Build recipes and
  runtime directives are separate inputs; relative directives paths resolve
  against the repository root.
- `01-bootstrap.sh` accepts only `ubuntu-24.04-minimal`. Its default is
  `debootstrap`; the tarball path requires a `24.04.x` version and matching
  SHA-256 entry before extraction. `pick_apt_mirror` fails on an unreachable
  explicit mirror instead of substituting a fallback.
- `02-provision.sh` checks the Mozilla signing-key fingerprint and pinned
  VSCodium package digest. Its generated `gallos-layout-toggle` only records
  a layout name and notifies; it does not apply XKB. Waybar's mode/countdown
  values are static placeholders. The tty1 autologin unit requires
  `/run/gallos/kiosk-ready`.
- `03-harden.sh` writes an initial IPv4 default-drop firewall independently of
  the runtime fallback selected by `build-iso.sh`. The neutral runtime profile
  remains the default fallback; effective runtime policy belongs to `gallosd`.
  USB Polkit denial is conditional on `security.allow_usb_storage=false`, and
  the baked udev denial rule is removed to preserve boot-storage discovery.
- `chroot_mount` guards existing mounts and recursively binds `/dev`.
  Provisioning and hardening retain these mounts for later stages;
  `04-optimize.sh` registers exit cleanup. Its removal options require `true`.
- `build-squashfs.sh` requires a matching initrd and Canonical-signed kernel,
  selecting the highest version-sorted `vmlinuz-*`. It excludes transient
  directory contents from SquashFS while retaining the directories themselves.
- `build-iso.sh` checks boot artifacts and signatures, uses the `GALLOS_BOOT`
  label, and creates password-protected GRUB editing with unrestricted normal
  and `toram` entries. Both entries pass `ipv6.disable=1`.
- `watch-qemu-boot.py:watch` has a 420-second deadline. Successful boot requires
  the serial `multi-user.target` marker and, when requested, the Secure Boot
  enabled marker. Rejection uses the bad-shim-signature marker. These checks
  do not establish graphical-session or physical-hardware acceptance.

## Side Effects

- Bootstrap deletes and recreates `ROOTFS`; tarball downloads use
  `/repo/.cache/base-images`. Provisioning and hardening download packages,
  run chroot commands, change users/services/configuration, and rebuild initramfs.
  Optimization may remove documentation and caches or replace locale settings.
- `chroot_mount` mounts proc/sys/dev and copies the builder's `resolv.conf`;
  `chroot_umount` attempts lazy unmounts and tolerates failures.
- Packaging replaces SquashFS and ISO outputs and mutates the staging tree.
  `copy_directives_profile` removes legacy top-level policy files;
  `copy_remote_policy_url` removes any previous source file before processing
  the new value. ISO assembly removes an output symlink without following it.
- QEMU helpers start emulator processes; attached raw USB fixtures are writable.
  The serial watcher terminates its subprocess when finished. Firmware variables,
  tampered ISOs, and compiler samples use temporary working directories.
  `make-test-usb-image.sh` truncates and populates its requested output path.

## Verification

Run the repository gate from the repository root:

```bash
./scripts/check.sh
```

It includes `build/tests/` and ShellCheck for these shell scripts. The project's
Ruff configuration excludes `build/`. For a built image and a testing host with
QEMU/OVMF, the separate boot checks include:

```bash
bash build/scripts/test-iso-qemu.sh --smoke
bash build/scripts/test-iso-qemu.sh --secure-boot --smoke
bash build/scripts/test-secure-boot-rejection.sh
```

See `docs/BUILD_SYSTEM.md` for builder/chroot verification setup and `ROADMAP.md`
for remaining image, graphical, and physical acceptance requirements. Listing
these commands does not record a successful image validation run.

### Contest Python and runtime acceptance

`install-contest-pypy.sh ROOTFS` installs the complete pinned PyPy 7.3.15
(Python 3.9.18) distribution under `/opt` after verifying its upstream SHA-256.
It exposes `/usr/local/bin/pypy3` without replacing the OS `/usr/bin/python3`.
The inventory is `/usr/share/gallos/contest-python.tsv` alongside the installed
package inventory. `verify-toolchains.sh` checks both runtime identity and the
system TOML parser.
