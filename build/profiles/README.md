# GallosOS Build Profiles (`build/profiles/`)

This directory contains declarative build manifests (**`*.build.toml`**) used exclusively by the containerized ISO build pipeline (`gallos-builder`).

---

## 🧭 Purpose: Build-Time Recipes (`build.toml`) vs. Runtime Directives (`gallos.toml`)

GallosOS enforces a strict separation between **Build-Time OS Recipes** and **Run-Time Contest Policies**:

| Layer | Configuration File | Location | Consumed By | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Build-Time** | `*.build.toml` | `build/profiles/` | `gallos-builder` (Podman/Docker) | Compiles the immutable base OS rootfs (`filesystem.squashfs`), Linux kernel, Wayland kiosk stack, and hybrid bootloader into an ISO. |
| **Run-Time** | `*.gallos.toml` | `examples/`, `/boot/gallos/` | `gallosd` (Python systemd service) | Evaluates competition schedules, dynamically locks down `nftables` firewall rules, switches wallpapers, manages USB storage access, and configures kiosk UX. |

For contest blueprints and tournament configurations, see [`examples/`](../../examples/README.md).

---

## ❓ Why is there only one profile (`universal.build.toml`)?

The runtime profiles in [`examples/`](../../examples/) cover neutral practice,
CPC-GALLOS club use, multi-judge training, and Organizer-configured contests.
The build still uses one `universal.build.toml` recipe.

The reasons are architectural:

### 1. The Single Universal Base ISO Architecture (The MVP Release Image)
For the GallosOS Minimum Viable Product (MVP), **only one official `.iso` is compiled and distributed**. Its embedded fallback is `examples/neutral.gallos.toml`: open practice with GallosOS identity. A strict official contest needs an Organizer policy with the correct judge and schedule. The underlying operating system stack is shared across club sessions, training, and contests.

[`gallosd`](../../daemon/) reads `gallos.toml` for implemented scheduling, network, and USB restrictions. This shared base avoids an image recipe per event, but it does not implement every catalog feature: dynamic countdown/menu integration, optional IDE provisioning, and other workstation controls remain roadmap items.

### 2. The Universal Reference Baseline
[`universal.build.toml`](./universal.build.toml) is the canonical recipe. Its source provisions:
- Containerized bootstrapping via `debootstrap` or verified `ubuntu-base` tarballs.
- Hybrid UEFI (Canonical signed shim + GRUB) and Legacy PC-BIOS booting.
- Live system OverlayFS layering and `casper` live-boot hooks.
- Base Wayland kiosk desktop packages.

It also declares the selected six toolchain families and core applications. Image acceptance is tracked separately in [`ROADMAP.md`](../../ROADMAP.md#release-acceptance); a recipe declaration is not proof of compiler, desktop, or physical hardware behavior.

### 3. Modular Layering (`.gsm`) in Phase 6
The planned expansion mechanism packages specialized software as `.gsm` SquashFS layers. Casper's layer-mounting mechanism exists, but this repository has no packaged `.gsm` bundles and ISO copying from `[modules].bundle` remains unimplemented. Core toolchains are provisioned directly into the base; optional module delivery is Phase 6 work.

---

## 🛠️ When should you create a custom `*.build.toml`?

You only need to create a new profile in `build/profiles/` if you are compiling a bespoke base image (Track 2 deployment):

1. **Future Alternate `base_os` Support:** Additional bases require implementation changes; the current bootstrap accepts only `ubuntu-24.04-minimal`. A custom profile alone cannot enable a different release (see [`docs/ARCHITECTURE.md` § 3.1](../../docs/ARCHITECTURE.md)).
2. **Resource-Constrained Environments (Tier 0):** Creating a stripped-down profile (e.g. console-only, minimal RAM footprint) for older 1–2 GB RAM lab workstations.
3. **Hardware-Specific Driver Ingestion:** Baking in proprietary GPU drivers (such as NVIDIA DKMS packages) or custom kernel modules directly into the base squashfs layer.

---

## 🚀 Building an ISO with a Profile

To build an ISO using a specific build profile, run from the repository root:

```bash
# Build using the default universal profile (build/profiles/universal.build.toml)
# Export GALLOS_GRUB_PASSWORD_HASH first (see docs/BUILD_SYSTEM.md).
make -C build iso

# Build a custom ISO and bundle a runtime profile as its fallback policy
make -C build iso \
  CONFIG=profiles/my-custom.build.toml \
  DIRECTIVES_PROFILE=examples/maratona-sbc.gallos.toml \
  REMOTE_POLICY_URL=https://example.org/gallos.toml
```

`CONFIG` selects the build-time OS recipe. `DIRECTIVES_PROFILE` separately selects the runtime `.gallos.toml` to bundle as the ISO's local fallback. Its path is relative to the repository root; if omitted, the ISO uses `examples/neutral.gallos.toml`. Optionally, `REMOTE_POLICY_URL` embeds a build-trusted HTTPS source separately from the fallback TOML. The profile on the approved boot medium takes precedence over remote policy and the bundled fallback. The official ISO sets neither custom input.

The output image is named after the build profile: the default produces `build/output/gallosos-universal-amd64.iso` (also available as `gallos-os-amd64.iso`), while the custom example produces `build/output/gallosos-my-custom-amd64.iso`.
