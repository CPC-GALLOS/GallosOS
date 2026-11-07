# GallosOS Live Image Build

## Overview

This directory owns the containerized pipeline that creates the Live root
filesystem, SquashFS, and BIOS/UEFI ISO. It consumes a build recipe, copies the
runtime daemon and inherited boot hooks from the repository, and embeds a
separately selected runtime fallback policy.

The [Containerfile](./Containerfile) supplies the Ubuntu 24.04 builder tools.
The [Makefile](./Makefile) launches the pipeline; the detailed stage and image
verification contracts are in [scripts/README.md](./scripts/README.md).

## Interface

Run these Make targets from the repository root:

| Target | Behavior |
| :--- | :--- |
| `make -C build image` | Build the local `gallos-builder` container image. |
| `make -C build iso` | Build the builder image, then run `scripts/run-pipeline.sh` inside it. |
| `make -C build clean` | Delete `build/output/`, first attempting cleanup through `podman unshare`. |

The Makefile accepts these settings for `iso`:

- `CONFIG`: build recipe, defaulting to `profiles/universal.build.toml`, resolved
  from the container's `/repo/build` working directory.
- `DIRECTIVES_PROFILE`: optional runtime fallback file, resolved relative to
  the repository root when not absolute. Empty selects
  `examples/neutral.gallos.toml`.
- `REMOTE_POLICY_URL`: optional trusted HTTPS source, staged separately from
  the fallback policy. Empty leaves no embedded remote source.
- `GALLOS_GRUB_PASSWORD_HASH`: required environment variable containing the
  GRUB PBKDF2-SHA512 hash; see `docs/BUILD_SYSTEM.md` for credential preparation.
- `CONTAINER_ENGINE`: optional engine override; automatic discovery prefers
  Podman, then Docker, and fails if neither is available.

`scripts/run-pipeline.sh:ISO` derives the image name from `CONFIG`'s basename:
`build/output/gallosos-<profile>-amd64.iso`. The universal recipe additionally
creates the `gallos-os-amd64.iso` compatibility symlink. Assembly emits sibling
`.sha256` and `.boot-packages.txt` files. Intermediate trees are `output/rootfs/`
and `output/staging/`.

## Subdirectories & Boundaries

- [scripts](./scripts/README.md): ordered build stages, shared helpers, and
  explicit rootfs/QEMU verification entry points.
- [profiles](./profiles/README.md): declarative build recipes; distinct from
  Organizer runtime policies in `examples/`.
- `assets/`: build assets; no standalone execution interface.
- `tests/`: source-level build regression tests, included by the repository gate.
- `output/`: generated images and intermediate trees, not maintained source.

## Invariants

- `Makefile:iso` invokes `run-pipeline.sh` inside the builder at `/repo/build`.
  The stage order is bootstrap, provision, harden, optimize, SquashFS, then ISO.
  The pipeline validates its GRUB hash and optional policy inputs before bootstrap.
- `scripts/01-bootstrap.sh:base_os` accepts only `ubuntu-24.04-minimal`.
  The declared recipe does not by itself add support for another base system.
- `scripts/build-iso.sh:DEFAULT_DIRECTIVES` selects the neutral practice
  fallback. Organizer restrictions require the appropriate runtime policy;
  the initial firewall written by `03-harden.sh` is a separate build product.
- `scripts/build-squashfs.sh:vmlinuz` and `build-iso.sh` check required signed
  boot artifacts before packaging. Build-time checks and emitted files do not
  establish successful firmware boot, runtime enforcement, or release acceptance.
- `scripts/build-iso.sh` does not populate recipe-declared `.gsm` bundles.
  Provisioning the Casper mounting hook and delivering module bundles are
  separate capabilities.

## Side Effects

- `Containerfile:RUN` downloads and installs builder packages. `Makefile:iso`
  runs a privileged container with the repository mounted read/write at `/repo`
  and SELinux labeling disabled for that invocation.
- Stages download packages, use chroot mounts, replace the rootfs, modify its
  users and service configuration, and write staging and ISO artifacts.
  Tarball bootstrap caches downloads under the repository's `.cache/base-images/`.
- `Makefile:clean` recursively deletes `build/output/`. The pipeline and cleanup
  share fixed output paths, so those paths must not hold unrelated data.
- QEMU helpers run separately from the ISO build and can write to an attached
  raw test image. See the script contract for temporary-file and subprocess effects.

## Verification

From the repository root:

```bash
./scripts/check.sh
```

The gate includes `daemon/tests/`, `build/tests/`, and ShellCheck for build shell
scripts. Rootfs toolchain checks and firmware boot checks are separate commands
documented in [scripts/README.md](./scripts/README.md) and `docs/BUILD_SYSTEM.md`.
Graphical contestant-session and physical-hardware acceptance remain distinct
from these repository checks; consult `ROADMAP.md` for acceptance status.
