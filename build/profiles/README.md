# GallosOS Build Profiles (`build/profiles/`)

This directory contains declarative build manifests (**`*.build.toml`**) used exclusively by the containerized ISO build pipeline (`gallos-builder`).

---

## 🧭 Purpose: Build-Time Recipes (`build.toml`) vs. Runtime Directives (`gallos.toml`)

GallosOS enforces a strict separation between **Build-Time OS Recipes** and **Run-Time Contest Policies**:

| Layer | Configuration File | Location | Consumed By | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Build-Time** | `*.build.toml` | `build/profiles/` | `gallos-builder` (Podman/Docker) | Compiles the immutable base OS rootfs (`filesystem.squashfs`), Linux kernel, Wayland kiosk stack, and hybrid bootloader into an ISO. |
| **Run-Time** | `*.gallos.toml` | `examples/`, `/boot/gallos/` | `gallos-daemon` (Python systemd service) | Evaluates competition schedules, dynamically locks down `nftables` firewall rules, switches wallpapers, manages USB storage access, and configures kiosk UX. |

For contest blueprints and tournament configurations, see [`examples/`](../../examples/README.md).

---

## ❓ Why is there only one profile (`universal.build.toml`)?

New contributors and contest organizers often ask why there are six contest blueprints in [`examples/`](../../examples/) (`icpc-onsite`, `maratona-sbc`, `ioi-cms`, `codeforces-training`, `icpc-online-exam`, `omegaup-omi`), but only one build profile (`universal.build.toml`) in this directory.

The reasons are architectural:

### 1. The Single Universal Base ISO Architecture (The MVP Release Image)
For the GallosOS Minimum Viable Product (MVP), **only one official `.iso` is compiled and distributed**. The underlying operating system stack — Ubuntu 24.04 LTS minimal, Linux HWE kernel, Labwc Wayland compositor, Waybar status bar, foot terminal, audio, and device management — is identical across collegiate contests, high school olympiads, and training camps.

All contest-specific behaviors (allowed judge IPs, IDE choices, countdown clocks, USB lockdown policies) are applied dynamically at boot by [`gallos-daemon`](../../daemon/) reading a `gallos.toml` file. **Organizers do not compile custom ISOs for every competition — the single universal ISO runs them all.**

### 2. The Universal Reference Baseline
[`universal.build.toml`](./universal.build.toml) is the canonical, maintainer-tested recipe. It validates:
- Containerized bootstrapping via `debootstrap` or verified `ubuntu-base` tarballs.
- Hybrid UEFI (Canonical signed shim + GRUB) and Legacy PC-BIOS booting.
- Live system OverlayFS layering and `casper` live-boot hooks.
- Base Wayland kiosk desktop packages.

### 3. Modular Layering (`.gsm`) in Phase 6
Rather than creating separate, monolithic base OS builds for different programming environments (e.g. a separate 4 GB ISO for IOI and a separate 4 GB ISO for ICPC), GallosOS packages specialized toolchains as modular Gallos Software Modules (`.gsm` SquashFS layers). These will be pre-bundled or dropped into `/gallos/modules/` without recompiling the base OS.

---

## 🛠️ When should you create a custom `*.build.toml`?

You only need to create a new profile in `build/profiles/` if you are compiling a bespoke base image (Track 2 deployment):

1. **Targeting an Alternate `base_os`:** e.g., building against `ubuntu-22.04-minimal` for legacy hardware or `ubuntu-26.04-minimal` for bleeding-edge silicon (see [`docs/ARCHITECTURE.md` § 3.1](../../docs/ARCHITECTURE.md)).
2. **Resource-Constrained Environments (Tier 0):** Creating a stripped-down profile (e.g. console-only, minimal RAM footprint) for older 1–2 GB RAM lab workstations.
3. **Hardware-Specific Driver Ingestion:** Baking in proprietary GPU drivers (such as NVIDIA DKMS packages) or custom kernel modules directly into the base squashfs layer.

---

## 🚀 Building an ISO with a Profile

To build an ISO using a specific build profile, run from the repository root:

```bash
# Build using the default universal profile (build/profiles/universal.build.toml)
make -C build iso

# Build using a custom profile
make -C build iso CONFIG=profiles/my-custom.build.toml
```

The output image is named after the build profile: the default produces `build/output/gallosos-universal-amd64.iso` (also available as `gallos-os-amd64.iso`), while the custom example produces `build/output/gallosos-my-custom-amd64.iso`.
