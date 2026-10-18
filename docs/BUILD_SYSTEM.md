# Containerized Build Pipeline (`build.toml`)

GallosOS uses a **Podman/Docker container build system** (`gallos-builder`) to limit host-side dependencies and provide a repeatable build environment. Containerization does not guarantee bit-for-bit reproducibility across hosts or runs. GallosOS is designed for infrastructure-agnostic deployment, but each venue integration remains separately scoped and validated.

The ISO assembler uses Ubuntu's packaged signed shim, GRUB, and kernel and writes both BIOS and EFI boot entries. It fails if the kernel or GRUB cannot be verified against Canonical's bundled certificate. It places `md5sum.txt` inside the ISO for Casper's media check and writes boot package versions and SHA-256 hashes alongside the ISO. Build verification is separate from physical-machine compatibility.

Before building, generate a GRUB password hash with `grub-mkpasswd-pbkdf2` inside the builder container and export its `grub.pbkdf2.sha512...` output as `GALLOS_GRUB_PASSWORD_HASH`. The Makefile forwards this environment variable without expanding its value into the container command. The pipeline rejects missing or malformed hashes before bootstrap. This credential protects menu editing and the GRUB command line; normal boot remains unrestricted. BIOS embeds the `password_pbkdf2` module and its dependencies. Password interaction on both firmware paths still requires a rebuilt-image boot test.

To generate the hash without host-installed GRUB tools:

```sh
make -C build image
podman run --rm -it gallos-builder grub-mkpasswd-pbkdf2
read -r -p 'Paste the generated GRUB hash: ' GALLOS_GRUB_PASSWORD_HASH
export GALLOS_GRUB_PASSWORD_HASH
```

Use `docker` in place of `podman` when that is your container engine. The ISO boot CI job generates an ephemeral credential solely for its verification image.

```sh
make -C build iso
bash build/scripts/test-iso-qemu.sh --secure-boot --smoke
bash build/scripts/test-iso-qemu.sh --secure-boot --toram
bash build/scripts/test-secure-boot-rejection.sh build/output/gallosos-universal-amd64.iso
```

The build runs `debootstrap`, `mksquashfs`, and `xorriso` inside the builder container, avoiding installation of those build tools on the host. Host container-runtime and virtualization setup are still required for building and testing.

---

## 1. The Holy Trinity of GallosOS Configurations

GallosOS separates concerns across three distinct TOML configuration files using standardized compound extensions:

| Config File | Compound Extension | Phase | Description | Web UI? |
| :--- | :--- | :--- | :--- | :--- |
| **`build.toml`** | `*.build.toml` (e.g. `universal.build.toml`) | **Build-Time** | Used by the `gallos-builder` container to generate a custom ISO (strip blobs, inject apt packages). | ❌ No |
| **`gallos.toml`** | `*.gallos.toml` (e.g. `icpc-onsite.gallos.toml`) | **Run-Time** | Organizer policy and mode logic (`Contest`/`Event`/`Default`). | Planned Config Builder |
| **`machine.toml`** | `*.machine.toml` (e.g. `pc-14.machine.toml`) | **Run-Time** | Optional local workstation identity metadata. | No; prepare the local file manually |

### 1.1 The Single Universal Base ISO Principle

A critical design choice in GallosOS is the decoupling of the **immutable operating system base** from **contest-specific runtime rules**:

- **Selected Universal Base:** The current `universal.build.toml` profile is the implemented build target for the selected release core. Per-event mode behavior can be configured without adding the planned optional module catalog.
- **Runtime Policy:** Supported network, browser, storage, mode, and machine-identity directives are loaded by `gallosd`. A policy field does not imply a UI control: mode-aware launcher/IDE selection, live countdowns, and printing remain planned work.
- **Directory Roles:** Build manifests live in [`build/profiles/`](../build/profiles/README.md) (used by system builders), whereas runtime competition blueprints live in [`examples/`](../examples/README.md) (used by contest organizers).

The official universal ISO bundles `examples/neutral.gallos.toml` as its fallback and has no remote policy source. Organizers building a bespoke ISO can select a different runtime fallback independently of the build manifest with `DIRECTIVES_PROFILE`, for example `make -C build iso CONFIG=profiles/my-custom.build.toml DIRECTIVES_PROFILE=examples/maratona-sbc.gallos.toml`. To enable online policy updates, optionally pass a build-trusted HTTPS URL with `REMOTE_POLICY_URL=https://example.org/path/gallos.toml`. The ISO embeds this URL separately from the policy file; the selected local profile is used offline and remains the startup fallback. Policies on `/etc` or the approved boot medium take precedence over remote updates. See [`CONFIG_SPEC.md` §2](./CONFIG_SPEC.md#2-configuration-delivery-methods) for polling and cache behavior.

---

## 2. Declarative ISO Generation (`build.toml`)

Rather than maintaining fragile Bash scripts with hardcoded `apt-get` commands, organizers feed a `build.toml` manifest into the container pipeline. This defines exactly what gets baked into the immutable `rootfs.squashfs` before the ISO is stitched together.

### Example `build.toml` Blueprint

```toml
[build]
base_os = "ubuntu-24.04-minimal"
kernel = "linux-generic-hwe-24.04"
target_arch = "amd64"
bootstrap_method = "debootstrap"  # or "tarball" — see § 2.2
ubuntu_base_version = "24.04.5"   # required when bootstrap_method = "tarball"
apt_mirror = "auto"               # or an explicit mirror URL — see § 2.2

[optimization]
# Strip down the OS to save RAM and USB space for Tier 0 (low-resource) environments
strip_man_pages = true
strip_docs = true
remove_apt_cache = true
locales = ["en_US.UTF-8", "es_MX.UTF-8"]

[packages]
# Base packages permanently baked into the rootfs (No .gsm required)
preinstall_apt = [
    "curl",
    "git",
    "python3-pip",
    "valgrind",
    "gdb"
]

[modules]
# Which GallosOS Software Modules (.gsm) to pre-bundle into the final ISO's /gallos/software/ directory
bundle = [
    "langs/gcc",
    "langs/openjdk",
    "programming/vscodium",
    "programming/vim",
    "tools/foot"
]

[security]
# Static build-time security posture (docs/ANTI_CHEAT_AND_SECURITY.md §3)
disable_ipv6 = true
judge_ips = ["192.168.50.10"]
venue_controller_ip = "192.168.50.1"
local_dns_ip = "192.168.1.1"
telemetry_dns_blacklist = [
    "1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4",
    "9.9.9.9", "9.9.9.10", "149.112.112.10", "149.112.112.112",
]
blocked_tcp_ports = [22, 853]
allow_usb_storage = false
```

### 2.1 Current `base_os` Support

The current bootstrap script accepts `ubuntu-24.04-minimal` and rejects other `base_os` values. Alternate Ubuntu releases and compatible kernel/HWE pairings require implementation and validation; setting another string in a manifest does not add support. See [`ARCHITECTURE.md` §3.1](./ARCHITECTURE.md#31-base_os-version-tiers-buildtoml).

### 2.2 `bootstrap_method` and `apt_mirror` (Stage 1 source)

`bootstrap_method` picks how Stage 1 builds the base rootfs:

- **`"debootstrap"` (default):** runs `debootstrap` live inside the container against `apt_mirror`. This is the default specifically because mirror flexibility genuinely exists at this layer — Canonical's apt archive is broadly mirrored (see `launchpad.net/ubuntu/+cdmirrors` for the official list) and the same mirror choice also serves Stage 2's package installs, since `debootstrap` configures the target's `sources.list` to match.
- **`"tarball"`:** requires `build.ubuntu_base_version` (for example, `24.04.5`) and uses the matching Canonical `ubuntu-base-<version>-base-amd64.tar.gz` snapshot. It reads `.cache/base-images/` first and downloads the exact version from Canonical's release archive if it is not cached, then verifies it against the corresponding entry in `SHA256SUMS`. The selected version must remain available from Canonical or in the local cache; update the profile when selecting a newer point release. This path supports offline builds with a pre-populated cache and avoids silently changing the base snapshot.

`apt_mirror` controls which apt mirror `debootstrap` (and Stage 2's `apt-get`) use:

- **`"auto"` (default):** tries an ordered fallback list of independently-verified mirrors (`build/scripts/lib-mirrors.sh`), first reachable one wins.
- **An explicit URL** (e.g. `"http://us.archive.ubuntu.com/ubuntu/"`): pins one mirror. If it's unreachable the build fails with a clear error rather than silently substituting another — an organizer who names a specific mirror (e.g. an internal proxy) should get a clear signal, not a silent swap.

`debootstrap`'s own default only writes a bare `main`-component, no-pockets `sources.list` line — no `restricted`/`universe`/`multiverse`, and no `-updates`/`-backports`/`-security`. The pipeline overwrites it after bootstrapping with all four components across `$SUITE`, `$SUITE-updates`, and `$SUITE-backports` on the chosen `apt_mirror`, plus `$SUITE-security` pinned to `security.ubuntu.com` specifically (not the general mirror — community mirrors don't reliably mirror the security pocket promptly; this matches Canonical's own convention).

### 2.3 Build-Time Caching and I/O

**What's cached today.** The only build-speed cache in the pipeline is `.cache/base-images/`, described in §2.2 above — it applies exclusively to `bootstrap_method = "tarball"`. Nothing else in the pipeline is cached across runs:

- **No apt-package cache.** `build/scripts/01-bootstrap.sh` deletes and recreates `$ROOTFS` (`rm -rf "$ROOTFS"`) at the start of every run, so Stage 2's `apt-get install` re-downloads every package from `apt_mirror` on every `make iso` invocation.
- **No container layer caching of ISO contents.** Stages 1–5 execute as `podman run` invocations of shell scripts against a bind-mounted host directory (`build/Makefile`: `-v $(REPO_ROOT):/repo:Z`), not `RUN` instructions in a Containerfile — so ordinary Docker/Podman image-layer caching doesn't apply to them. Layer caching only benefits rebuilds of the separate `gallos-builder` tool image (`build/Containerfile`, the container that *holds* `debootstrap`/`mksquashfs`/`xorriso`), which is unrelated to what ends up on the ISO.
- **No BuildKit cache mounts.** The pipeline uses plain `podman build`/`podman run`, not `docker buildx`, so `--mount type=cache` syntax isn't applicable here.

Don't confuse this with the `optimization.remove_apt_cache` flag (§2 above, applied in Stage 4 / `build/scripts/04-optimize.sh`): that purges `/var/cache/apt/archives` and `/var/lib/apt/lists/*` at the *end* of the pipeline to shrink the shipped ISO's disk footprint — it's a size optimization for the output image, not a build-speed cache.

**Optional build-host tmpfs for I/O.** This section describes a *build-host* tmpfs — RAM-backed storage on the machine running `make iso` — which is unrelated to the *runtime* tmpfs documented in `docs/ARCHITECTURE.md` § 4, item 3 (the ephemeral OverlayFS upper layer inside the *booted* live ISO). The two share a name but nothing else; see that section if you came here from there.

`build/output/` (holding `rootfs/` and `staging/`, per `build/scripts/run-pipeline.sh`) lives under the same host bind mount as the rest of the repo, so every file write across Stages 1–5 lands on whatever filesystem backs that path on the host. Stage 5a's `mksquashfs` call (`build/scripts/build-squashfs.sh`) is the most I/O-concentrated single step — it reads the entire `$ROOTFS` tree and writes one large compressed archive.

An operator with spare RAM can point `build/output/` at a tmpfs before invoking `make iso`, with no pipeline changes required — for example:

```sh
sudo mount -t tmpfs -o size=8G tmpfs build/output/
```

(or bind a `/dev/shm`-backed directory there instead). Rootfs population (Stages 2–4) and squashing (Stage 5a) are disk-I/O-bound operations — reading/writing many files, then one large archive — so routing them through RAM instead of a disk-backed filesystem removes that disk round-trip. No speedup is claimed here; this is architectural reasoning about where the I/O goes, not a benchmarked result.

Caveats: `size=8G` is not a spec, just headroom above one observed data point — a `universal.build.toml` run on this machine produced a ~1.4 GB rootfs and ~1 GB of staging output (`$STAGING/casper/filesystem.squashfs` alone was ~900 MB), so `build/output/` needs roughly 2.5 GB free plus room for the final ISO; a profile pulling in more `.gsm` modules or `[optimization]` settings will need more. Re-check with `du -sh build/output` against your own profile rather than assuming this figure holds. tmpfs contents don't survive a reboot or unmount, so this is a purely transient build accelerant, not a substitute for `.cache/base-images/`'s cross-run persistence. This is a manual, opt-in host-level step; nothing in `build.toml`, the `Makefile`, or the pipeline scripts currently detects, requires, or automates it.

---

## 3. The 5-Stage Container Pipeline (`Makefile` / `Containerfile`)

When a developer runs `make iso CONFIG=profiles/universal.build.toml`, the container executes the following stages internally:

### Stage 1: Base Bootstrap (`debootstrap` or `ubuntu-base` tarball)

Controlled by `build.toml`'s `bootstrap_method` (§ 2.2). By default the container runs `debootstrap` against `apt_mirror` (`"auto"` picks the first reachable mirror from an ordered fallback list — `build/scripts/lib-mirrors.sh`). Setting `bootstrap_method = "tarball"` instead imports the exact `ubuntu_base_version` snapshot from `.cache/base-images/` or Canonical's archive and verifies its SHA256 checksum before extraction. Either path establishes the basic directory structure and populates `/dev`, `/proc`, and `/sys` for chrooting.

### Stage 2: Provisioning (`chroot`)

The builder enters the chroot environment and:

1. Installs the Linux kernel, casper live boot machinery, and system utilities.
2. Injects the GallosOS casper-bottom hook (`55gallos-live`).
3. Parses `build.toml` $\to$ `[packages]` and executes `apt-get install -y <packages>`.
4. For the universal recipe, installs Firefox from Mozilla's signed DEB repository and a pinned, SHA-256-checked VSCodium release. GCC, Clang, OpenJDK, Python/PyPy, Rust, Kotlin, Geany, and the local training proxy come from the configured Ubuntu package repositories. The image records installed package versions in `/usr/share/gallos/toolchains.tsv`.

After building, run the compiler smoke test against the generated rootfs:

```bash
podman run --rm --privileged --security-opt label=disable \
  -v "$PWD:/repo" -w /repo/build gallos-builder \
  bash scripts/verify-rootfs-toolchains.sh /repo/build/output/rootfs
```

Run this command from the repository root. It compiles and executes a small
program in every advertised language family and checks the browser, editor,
and proxy commands. The graphical browser/editor session still needs VM
acceptance.

### Stage 3: Security Lockdown & Resource Hardening (`chroot`)

Configures build inputs used by policy-scoped security mechanisms. The neutral profile remains open practice; the firewall does not represent a universal Zero-Trust or zero-leak guarantee.

1. Installs and enables `nftables` with an `inet` family default-DROP firewall for restricted modes, whitelisting judge IPs in Contest and dropping telemetry DNS.
2. Disables IPv6 via `/etc/sysctl.d/99-gallos-noipv6.conf` and kernel bootcmd parameters.
3. Prepares host-service USB-storage enforcement and Polkit rules according to the build policy. The build removes any coldplug-time class-08 Udev denial; the runtime helper adds an interface rule after boot-medium discovery.
4. Configures and enables the `earlyoom` daemon with `-n` D-Bus notification support.
5. Locks down virtual terminal switching (TTY1–6) via `logind.conf.d`, masking `autovt@.service`, and loading a stripped console keymap.
6. Hardens contestant privileges by purging `sudo` and locking the `root` account.

### Stage 4: Stripping & Optimization

To keep the Live OS memory footprint minimal (Crucial for `toram` boot):

1. Parses `build.toml` $\to$ `[optimization]`.
2. Deletes unused locales via `locale-gen`.
3. Purges `/usr/share/doc`, `/usr/share/man`, and `/var/cache/apt/archives`.

### Stage 5: Squash & Stitch (`mksquashfs` & `xorriso`)

1. **Stage 5a (Squash):** Compresses the entire optimized rootfs into `filesystem.squashfs` (using `zstd` for high-speed decompression in RAM).
2. **Stage 5b (ISO):** Sets up the GRUB bootloader for UEFI and Legacy BIOS with `ipv6.disable=1` and uses `xorriso` to output the final hybrid bootable image: `gallosos-<profile>-amd64.iso` (profile-derived from the `CONFIG` `*.build.toml` filename, e.g. `gallosos-universal-amd64.iso` from `profiles/universal.build.toml`). Set `GALLOS_GRUB_PASSWORD_HASH` to a GRUB PBKDF2 hash before building; the generated menu permits normal boot but requires authentication to edit entries or access the GRUB command line. The neutral practice example is bundled as `/gallos/config/baseline/baseline.gallos.toml`; an organizer's canonical `gallos.toml` or unique `*.gallos.toml` takes precedence at boot. The baseline stays in a subdirectory so automatic profile discovery does not count it. Copying `[modules]` `.gsm` bundles from `build.toml` onto the ISO's `/gallos/modules/` directory is not yet wired into `build-iso.sh` — the `.gsm` *mounting mechanism* (this stage's casper-side counterpart) is implemented per ROADMAP.md Phase 1, but populating an ISO with real bundled modules at build time is separate, still-open work.

---

## 3.1 Shell Script Validation

The pipeline's orchestration scripts (`build/scripts/*.sh`) are expected to pass [`shellcheck`](https://www.shellcheck.net/) before merge — run `shellcheck build/scripts/*.sh` locally, or `shellcheck -x build/scripts/*.sh` to also follow the `# shellcheck source=` directives in `01-bootstrap.sh`, `02-provision.sh`, `03-harden.sh`, and `04-optimize.sh` into their sourced libs (`lib-mirrors.sh`, `lib-chroot.sh`). This is now enforced automatically: `.github/workflows/ci.yml` runs ShellCheck against `build/scripts/*.sh` on every push/PR to `main`, and `.pre-commit-config.yaml` runs it on every local commit. See [`docs/DEVELOPMENT.md`](./DEVELOPMENT.md) for the full lint/test/CI pipeline, including the Python (`ruff`/`pytest`) checks that apply to `daemon/` rather than to these build scripts.

---

## 4. MOK Signing Key Persistence (Optional Proprietary Kernel Modules)

**Status: planned Phase 4 driver support.** The module and persistent MOK-signing workflow below are design requirements; the current signed Ubuntu boot chain does not implement them.

The `drivers/nvidia-proprietary` `.gsm` module (see `docs/HARDWARE_COMPATIBILITY.md` § 1.3) carries a DKMS-built, out-of-tree kernel module, which requires a Machine Owner Key (MOK) signature to load under SecureBoot. Because organizers enroll that MOK **once per physical machine** (a venue-setup step, not a per-boot one), the signing key itself must stay stable across ISO rebuilds — a rotated key would silently invalidate every previously-enrolled machine's trust.

- `gallos-builder` generates the MOK signing keypair once (outside of any single `make iso` invocation) and persists it as a pipeline secret, reusing it to sign the `nvidia-dkms` module on every subsequent build.
- Each release ships the corresponding public certificate alongside the ISO so organizers can run `mokutil --import` during venue setup.
- This key is independent of, and unrelated to, Canonical's `shim`/kernel signing keys described in `docs/HARDWARE_COMPATIBILITY.md` § 1.2 — those cover the stock boot chain; the MOK covers only the opt-in proprietary module.

---

## 5. In-Place USB Delta Updates and Layer Injection (`gallos-inject`)

**Status: planned Phase 5 Organizer tooling.** The following tiers and CLI examples specify intended behavior; `gallos-inject` and `gallos-flash` are not implemented commands in this repository.

While `gallos-flash` is engineered for the initial mass provisioning of raw USB drives across large workstation fleets, organizers frequently need to make minor contest adjustments (e.g. updating contest schedules, changing whitelisted URLs, swapping event wallpapers, adding an offline IDE extension, or adjusting GPU kernel flags) on **already-flashed USB drives**.

Re-flashing an entire 4.5–6.0 GB raw disk image just to update a few kilobytes of configuration introduces massive unnecessary I/O, wears down USB NAND flash cells, and wipes any existing user `event-data` partition.

Inspired by the battle-tested injection scripts developed during production deployments in [`CPC-GALLOS/icpc-gpm-uaa-huronos`](https://github.com/CPC-GALLOS/icpc-gpm-uaa-huronos), GallosOS formalizes **`gallos-inject`** as an official organizer CLI tool for in-place, non-destructive delta updates.

### 5.1 The 4-Tier Delta Injection Model

```mermaid
flowchart TD
    subgraph Target USB Drive ["Target USB Drive (GALLOS_BOOT FAT32)"]
        ConfigPath["/gallos/config/<br>• gallos.toml<br>• wallpaper.png"]
        ModulesPath["/gallos/modules/<br>• *.gsm Software Packages"]
        CustomLayerPath["/gallos/system/<br>• 99-custom.gsm"]
        BootloaderPath["/boot/grub/grub.cfg<br>/EFI/BOOT/grub.cfg"]
    end

    T1["Tier 1: Config & Branding Delta<br>(Direct Filesystem Copy)"] --> ConfigPath
    T2["Tier 2: Modular .gsm Packages<br>(Drop-in Module Discovery)"] --> ModulesPath
    T3["Tier 3: Custom System Layer Overrides<br>(Unsquash / Patch / Repack 99-custom.gsm)"] --> CustomLayerPath
    T4["Tier 4: Kernel Parameters & Boot Flags<br>(In-place GRUB cfg edit)"] --> BootloaderPath
```

1. **Tier 1: Configuration & Branding Delta (`gallos.toml` & Wallpapers)**
   - **Mechanism:** Direct filesystem write to `/gallos/config/gallos.toml` and `/gallos/config/wallpaper.png` on the FAT32 `GALLOS_BOOT` partition.
   - **I/O Scope:** Kilobytes of plain text/image data.
   - **Advantage:** No SquashFS repacking or chroot operations invoked.

2. **Tier 2: Modular Software Package Management (`/gallos/modules/*.gsm`)**
   - **Mechanism:** Standalone SquashFS packages. The early-boot initramfs dynamically stacks all `.gsm` modules present in `/gallos/modules/` into the live OverlayFS stack.
   - **I/O Scope:** Limited to the size of the added or replaced `.gsm` package (e.g. `programming-vsc-cph.gsm`).
   - **Advantage:** Adds compilers or IDE extensions without modifying the core `rootfs.squashfs` base image.

3. **Tier 3: Custom System Layer Overrides (`99-custom.gsm`)**
   - **Mechanism:** Reserved at the top of the OverlayFS layer stack. `gallos-inject` extracts `99-custom.gsm`, applies arbitrary files/scripts (e.g. emergency `udev` rules, custom dotfiles, offline deb packages, or driver quirks), recompresses it via `mksquashfs`, and updates `checksums.sha256`.
   - **I/O Scope:** Scoped exclusively to the lightweight override layer.
   - **Advantage:** Leaves the base OS completely untouched while permitting deep system tailoring.

4. **Tier 4: Bootloader & Kernel Tuning**
   - **Mechanism:** Modifies `/boot/grub/grub.cfg` and `/EFI/BOOT/grub.cfg` on the FAT32 partition.
   - **I/O Scope:** Kilobytes of configuration text.
   - **Advantage:** Toggles `toram` execution, adjust boot timeouts, or append hardware quirks (e.g. `nomodeset`, `nouveau.modeset=0`) in-place.

### 5.2 `gallos-inject` CLI Usage & Workflows

```bash
# Update runtime configuration without touching OS binaries:
gallos-inject --config examples/icpc-onsite.gallos.toml /dev/sdb1

# Replace event wallpaper:
gallos-inject --wallpaper assets/icpc-gpm-2026.png /dev/sdb1

# Inject an offline software module (.gsm):
gallos-inject --add-module build/modules/programming-vsc-cph.gsm /dev/sdb1

# Apply a folder of system-level custom overrides into 99-custom.gsm:
gallos-inject --custom-layer ./custom-lab-overrides/ /dev/sdb1

# Multi-target batch mode: Auto-detect all mounted GALLOS_BOOT drives and update in parallel:
gallos-inject --all-drives --config icpc-date3.gallos.toml --wallpaper gpm-wallpaper.png
```

---

## 6. Planned Release Artifact Distribution & Mirror Architecture

Phase 6 plans release publication and artifact hosting. No official release-download mirrors or Organizer CLI binaries are currently published by this repository. Any future channels should document artifact identity, signatures, and region-specific availability without promising download performance.

### 6.1 GitHub Release Considerations

* **Release asset limits:** Check the hosting provider's current limits when implementing artifact publication.
* **Artifact size:** Measure the actual release image before selecting a split or mirror strategy. Optional software that is not part of the selected core should not be included in estimates as if it were shipped.

### 6.2 Candidate Distribution Strategy

```mermaid
flowchart TD
    BuildPipeline["Release pipeline (planned)<br>(CI / Local Podman)"] --> Artifacts["Candidate artifacts<br>• ISO<br>• Checksums and signatures<br>• Organizer utilities (planned)"]

    Artifacts --> GH_Releases["Candidate: GitHub Releases<br>• Release artifacts and checksums"]
    Artifacts --> GDrive_Mirror["Optional secondary mirror<br>(hosting decision pending)"]
```

1. **Candidate GitHub Release Channel:** Define a release manifest, exact image checksums, and signing process in Phase 6. Check current hosting limits and download requirements when implementation begins; no artifacts are published here yet.

2. **Optional Secondary Mirror:** Hosting, ownership, artifact layout, and availability guarantees have not been selected. The previously proposed Google Drive mirror is not an active release channel.
