# Containerized Build Pipeline (`build.toml`)

GallosOS is designed to be **100% reproducible and infrastructure-agnostic**. To achieve this, the entire ISO generation process is isolated inside a **Podman/Docker Container Build System** (`gallos-builder`).

This approach completely eliminates host OS pollution and allows developers to build GallosOS on Linux, macOS, or Windows (via WSL2) without installing tools like `debootstrap`, `mksquashfs`, or `xorriso` on their local machines.

---

## 1. The Holy Trinity of GallosOS Configurations

GallosOS separates concerns across three distinct TOML configuration files:

| Config File | Phase | Description | Web UI? |
| :--- | :--- | :--- | :--- |
| **`build.toml`** | **Build-Time** | Used by the `gallos-builder` container to generate a custom ISO (strip blobs, inject apt packages). | ❌ No |
| **`gallos.toml`** | **Run-Time** | The global contest rules, branding, and mode logic (`Contest`/`Event`/`Default`). | ✅ **Yes (Config Builder)** |
| **`machine.toml`** | **Run-Time** | The physical identity of the specific workstation (Seat ID, Static IP). | ❌ No (Local Script) |

---

## 2. Declarative ISO Generation (`build.toml`)

Rather than maintaining fragile Bash scripts with hardcoded `apt-get` commands, organizers feed a `build.toml` manifest into the container pipeline. This defines exactly what gets baked into the immutable `rootfs.squashfs` before the ISO is stitched together.

### Example `build.toml` Blueprint

```toml
[build]
base_os = "ubuntu-24.04-minimal"
kernel = "linux-generic-hwe-24.04"
target_arch = "amd64"

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
```

---

## 3. The 4-Stage Container Pipeline (`Makefile` / `Containerfile`)

When a developer runs `make iso CONFIG=profiles/build-icpc.toml`, the container executes the following stages internally:

### Stage 1: Base Bootstrap (`debootstrap`)

The container pulls a pristine Ubuntu 24.04 core filesystem. It establishes the basic directory structure and populates `/dev`, `/proc`, and `/sys` for chrooting.

### Stage 2: Provisioning (`chroot`)

The builder enters the chroot environment and:

1. Installs the Wayland Kiosk core (`labwc`, `waybar`, `foot`).
2. Injects the `gallos-daemon` stateless scripts (Python).
3. Parses `build.toml` $\to$ `[packages]` and executes `apt-get install -y <packages>`.

### Stage 3: Stripping & Optimization

To keep the Live OS memory footprint minimal (Crucial for `toram` boot):

1. Parses `build.toml` $\to$ `[optimization]`.
2. Deletes unused locales via `locale-gen`.
3. Purges `/usr/share/doc`, `/usr/share/man`, and `/var/cache/apt/archives`.

### Stage 4: Squash & Stitch (`mksquashfs` & `xorriso`)

1. Compresses the entire optimized rootfs into `filesystem.squashfs` (using `zstd` for high-speed decompression in RAM).
2. Sets up the GRUB bootloader for both UEFI SecureBoot (`shim`) and Legacy BIOS (`grub-pc`).
3. Copies the `.gsm` files declared in `[modules]` into the ISO layout.
4. Uses `xorriso` to output the final hybrid, bootable image: `gallosOS-custom-amd64.iso`.
