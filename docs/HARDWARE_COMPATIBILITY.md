# GallosOS Hardware & Firmware Compatibility Specification

This document defines the architectural hardware baseline, bootloader targets, and firmware security requirements for GallosOS.

Hardware targets are requirements, not a certified machine matrix. See [`ROADMAP.md`](../ROADMAP.md#release-acceptance) for separate image, graphical, and physical acceptance gates; a VM result does not certify a physical workstation.

GallosOS targets a wide range of environments, from legacy BIOS workstations to modern UEFI Secure Boot laptops. Actual compatibility depends on image, firmware, and physical-machine acceptance.

---

## 1. Boot Firmware & Architecture

GallosOS uses a hybrid bootloader architecture designed to maximize boot compatibility across old and new host hardware.

### 1.1 Legacy BIOS (CSM) vs UEFI

- **Legacy BIOS (PC-BIOS / CSM):** The hybrid ISO includes a GRUB BIOS El Torito image and hybrid MBR. Verify the actual machine before venue deployment.
- **UEFI (Unified Extensible Firmware Interface):** The ISO includes an appended FAT EFI System Partition with Ubuntu's signed shim, GRUB, and MokManager. The ISO also carries their optical-media lookup paths.

### 1.2 The SecureBoot Advantage

The build uses Ubuntu's signed boot chain: Microsoft-trusted shim, Canonical-signed GRUB, and a Canonical-signed kernel. The builder rejects missing signatures and verifies GRUB and the kernel against Canonical's certificate. The complete Live ISO reached `multi-user.target` in QEMU with Secure Boot enforced; a modified kernel was rejected by GRUB in a separate negative test. Physical-machine validation is still required before organizer deployment.

> [!WARNING]
> **The Legacy Firmware Risk:** The official *Manual de Instalación de Huron OS para Delegados Estatales y Competidores* (OMI 2023) explicitly mandated that delegates and contestants disable both **Secure Boot** and **TPM (Trusted Platform Module)** in firmware. The manual accompanied this with a severe warning: disabling Secure Boot and TPM on modern Windows 11 laptops with BitLocker encryption active can trigger permanent boot failures, BitLocker recovery lockouts, and potential data loss.

GallosOS avoids requiring Secure Boot to be disabled by using:

1. **Canonical's Signed `shim` Bootloader:** Microsoft-trusted shim loads the GRUB bootloader.
2. **Canonical's Signed Linux Kernel:** We use the unmodified, upstream Ubuntu LTS kernel.
3. **In-Tree Kernel Modules in the Current Recipe:** The current recipe uses the Ubuntu kernel and does not include the planned out-of-tree NVIDIA module. Secure Boot validates signed boot components; it does not guarantee that every runtime file or policy is authentic.

**Trust boundary:** This conventional Secure Boot chain validates EFI executables and the kernel. It does not authenticate the mutable `gallos.toml`, the initrd, or SquashFS content. Firmware keys and revocation lists differ across machines, so organizers must test the actual venue hardware.

### 1.3 Planned Proprietary GPU Drivers & MOK Signing

An optional proprietary NVIDIA driver bundle is a Phase 4 roadmap item, not part of the current ISO or module catalog. Hardware using Nouveau or a proprietary driver has not been certified across a physical machine matrix.

- The current daemon does not select this module through `gallos.toml`; build-time module packaging and copying are also not implemented.
- If the project implements an out-of-tree DKMS driver, signing and Secure Boot enrollment will need a stable-key design and per-machine testing. Signing does not remove kernel taint, and MOK persistence must be verified on target firmware.
- See [`ROADMAP.md`](../ROADMAP.md#phase-4-contestant-workstation-features-beta-3) and [`BUILD_SYSTEM.md`](./BUILD_SYSTEM.md#4-mok-signing-key-persistence-optional-proprietary-kernel-modules) for status and the proposed build workflow.

### 1.4 Architecture Scope: 32-bit x86

The current build target is `amd64`; 32-bit x86 images are outside the supported scope. This is a GallosOS project decision, not a claim that every judge platform uses the same architecture or that local execution can guarantee parity with a judge.

The LP64 and ILP32 data models differ, including the width of `long` and pointers. Architecture can also affect available instructions, resource limits, and execution timings. Organizers should follow the judge's published compiler and runtime requirements; local tests do not establish identical judge behavior.

## 1.5 Intel Macs (Unvalidated Hardware)

Some venues may consider 64-bit Intel Macs as Live USB hosts. They fall within the `amd64` architecture target, but the project has no empirical acceptance matrix for Intel Mac models.

- **Architecture:** 64-bit Intel Macs are potential `amd64` hosts. 32-bit Intel Macs remain outside the supported scope under § 1.4.
- **Boot setup:** Organizers must confirm that the specific Mac can boot external EFI media. On T2-equipped Intel Macs, Startup Security Utility may need to permit external/removable-media boot. This is a per-machine firmware setting and must be checked before deployment.
- **Hardware validation:** Test the exact Mac model and year for display output, keyboard, trackpad, Wi-Fi, suspend behavior, and USB-C/Thunderbolt adapters. Apple-specific peripherals and older Broadcom wireless chips can require a wired connection or a supported USB Ethernet/Wi-Fi adapter.
- **Operational recommendation:** Keep a USB keyboard and a wired network or compatible USB network adapter available at venues using Intel Mac hardware. Prefer a direct USB boot test on every model family before contest day; QEMU validation does not establish physical Mac compatibility.
- **Security and data safety:** Booting the Live USB is intended to leave the internal macOS installation untouched, but organizers must not change Startup Security settings or repartition internal storage without the machine owner's authorization and a tested recovery process.

Treat each model as unvalidated until it passes direct boot and contestant-workflow checks.

### 1.6 Future Architecture Trajectory: ARM64 (AArch64)

The canonical build targets `x86_64` (`amd64`). ARM64 is a Phase 7 exploration target, not a supported build. The project has not collected hardware-demand data or validated ARM64 laptops.

Possible future evaluation areas include:

1. **Apple Silicon:** Device-specific boot, graphics, and input support would need evaluation through the Asahi Linux ecosystem.
2. **Qualcomm Snapdragon laptops:** Model-specific boot, graphics, firmware, and driver support would need testing; standard UEFI behavior should not be assumed for every device.
3. **Generic ARM single-board computers:** Outside the current Phase 7 laptop exploration scope.

Architecture can affect available instructions, memory behavior, and execution timings. Follow each contest's published judge architecture and compiler configuration; GallosOS makes no universal claim about judge hardware.

## 2. Hardware Requirements Matrix

The values below are provisional planning targets, not empirically established minimums or a certified hardware matrix. Device, workload, and image acceptance results belong in [`ROADMAP.md`](../ROADMAP.md#release-acceptance).

### 2.1 Standard Live Boot

- **Architecture:** The current ISO build targets `amd64` / `x86_64`.
- **Memory:** 4 GB is a provisional planning floor and 8 GB a planning recommendation for heavier IDE workloads. Neither threshold has been established by a GallosOS hardware benchmark. Actual memory use depends on the desktop, toolchain, contestant program, and writable `tmpfs` activity; EarlyOOM reduces risk but does not provide a memory limit.
- **USB capacity:** 16 GB or larger is a planning target. Confirm that the selected image and any partition layout fit the device. Read speed and sustained behavior vary by drive and host; test the intended combination.
- **Write behavior:** The SquashFS lower layer is read-only and volatile root changes use a `tmpfs` upper layer. Optional `event-data` is separate persistent storage and is written outside Contest when mounted. GallosOS does not claim that the boot device is never written.

### 2.2 `toram` Boot

Casper's `toram` path is present. Historical QEMU notes report RAM-copy behavior, but the next release-candidate check still needs to identify the image and capture evidence. A 16 GB machine is a planning target, not a measured minimum; available memory must cover the compressed image, runtime, applications, and writable `tmpfs` use.

Do not unplug the USB based on the boot option alone. First verify on the exact image that policy files, optional `event-data`, and other required resources are no longer being read from the device and that the intended workflow survives removal.

### 2.3 GPU and Display Adapter

The image uses the Ubuntu kernel and its available in-tree driver packages. That does not certify every Intel, AMD, or NVIDIA device, firmware revision, display output, or accelerated rendering path. Validate the exact machine and the graphical contestant session before deployment. The proprietary NVIDIA driver and MOK workflow remain planned Phase 4 work; see § 1.3.

---

## 3. Peripheral and Network Compatibility

- **Displays:** Labwc and Waybar are provisioned for the base session. Fractional scaling, multi-monitor behavior, suspend/resume, and display hot-plug have not been accepted across a physical device matrix.
- **Keyboards:** Configured layout application and a Waybar switcher remain Phase 4 work. The current `Super + Space` / `Alt + Shift` helper records a name from `us`, `latam`, `es`, or `br` and sends a notification; it does not change the active layout.

### 3.1 Broadcom and Other Wi-Fi Devices

The project has no accepted Wi-Fi hardware matrix. The current recipe does not explicitly select `firmware-b43-openfwwf` or an interactive network applet, so this document does not claim support for particular Broadcom chipsets. Check the firmware and driver required by the exact adapter; keep a wired or separately validated USB network adapter available where network access is required.

### 3.2 Enterprise and Campus Wi-Fi (IEEE 802.1X / WPA-Enterprise)

GallosOS currently installs NetworkManager, but the selected desktop does not include the described graphical network applet and `gallos.toml` has no consumed `wifi_profiles` setting. Interactive EAP setup and declarative profile provisioning are future requirements, not current BYOD support. Validate credentials, certificate handling, reconnect behavior, and the contestant workflow on an accepted image before advertising this capability.

The predecessor ConnMan issue documented in [`CPC-GALLOS/icpc-gpm-uaa-huronos`](https://github.com/CPC-GALLOS/icpc-gpm-uaa-huronos) is historical context; it does not demonstrate that GallosOS supports the same networks.

---

## 4. Planned Mass Flashing Hardware (`gallos-flash`)

`gallos-flash` is planned Phase 5 organizer tooling and is not implemented. The project has no measured concurrent-write throughput or supported-device matrix. The following are general planning considerations for a future flashing station, not GallosOS performance claims or mandatory hardware specifications.

Before large-scale use, test the actual host, hub, and USB drives together and verify every written image. Power and throughput depend on the hub topology, host controller, drive model, and number of simultaneous writes.

1. Consider a powered hub when its port power budget and the selected drives require it.
2. Check which ports share a host controller; more physical ports do not guarantee independent bandwidth.
3. Measure end-to-end write and verification time with the intended drive models before planning a deployment schedule.

## 5. Exploratory CPU Timing Considerations (Not Implemented)

The current build and runtime do not configure CPU governors, disable boost, offline sibling threads, pin workloads, or provide the named `run*` wrappers. The project has not benchmarked these ideas on target hardware; they are exploratory considerations, not active policy or guaranteed timing improvements.

Frequency scaling, thermal limits, power profiles, and scheduler behavior can affect local benchmark results. Any future change should measure its effect on representative hardware and account for battery, temperature, and sustained load.

The examples below are possible mechanisms to evaluate; they are not implemented through `gallosd` or a `[system.hardware]` configuration section:

### 5.1 Possible Frequency and Boost Controls

On supported hardware, a future tool could evaluate kernel CPU frequency interfaces such as:

- **Intel Processors (`intel_pstate`):**

  ```bash
  # Disable Intel Turbo Boost
  echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo
  # Example performance-limit controls; verify semantics for the active driver
  echo 100 > /sys/devices/system/cpu/intel_pstate/min_perf_pct
  echo 100 > /sys/devices/system/cpu/intel_pstate/max_perf_pct
  ```

- **AMD Processors (`cpufreq`):**

  ```bash
  # Disable AMD Core Performance Boost
  echo 0 > /sys/devices/system/cpu/cpufreq/boost
  ```

- **Frequency Governor:**
  A future implementation could evaluate setting `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` to `performance`. Effects on temperature, battery use, and sustained performance would need measurement.

### 5.2 Possible CPU Affinity Evaluation

On selected hardware, a future evaluation could measure the effect of:

1. **Virtual Sibling Thread Deactivation:**
   A future implementation could evaluate offlining selected logical CPUs (`echo 0 > /sys/devices/system/cpu/cpu<N>/online`). This changes scheduler placement and resource contention; it does not guarantee uncontended cache or faster execution.
2. **Process Affinity Pinning (`taskset`):**
   A future wrapper could optionally pin a test process to selected CPUs with `taskset -c <core>`. GallosOS does not currently provide the named run wrappers, and affinity pinning would not eliminate all scheduler or thermal variation.
