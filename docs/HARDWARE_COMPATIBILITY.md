# GallosOS Hardware & Firmware Compatibility Specification

This document defines the architectural hardware baseline, bootloader targets, and firmware security requirements for GallosOS.

To ensure maximum compatibility across diverse university lab environments and competitor laptops, GallosOS is engineered to support a wide spectrum of hardware—from legacy BIOS workstations to modern UEFI SecureBoot laptops.

---

## 1. Boot Firmware & Architecture

GallosOS uses a hybrid bootloader architecture to guarantee maximum boot success rates regardless of the host machine's age.

### 1.1 Legacy BIOS (CSM) vs UEFI

- **Legacy BIOS (PC-BIOS / CSM):** Fully supported. The Live USB includes an `mbr.bin` and the `grub-pc` payload in the boot sector. This ensures compatibility with older university lab computers (pre-2015) that do not support UEFI.
- **UEFI (Unified Extensible Firmware Interface):** Fully supported. The Live USB includes an EFI System Partition (ESP) with `grub-efi-amd64` binaries, supporting modern 64-bit UEFI firmware natively.

### 1.2 The SecureBoot Advantage

Unlike legacy contest distributions (like HuronOS) that relied on patching custom, out-of-tree filesystem modules (AUFS) into the Linux kernel—which inherently breaks cryptographic signatures and forces organizers to manually disable SecureBoot on hundreds of laptops—**GallosOS fully supports UEFI SecureBoot out of the box.**

GallosOS achieves this by leveraging:

1. **Canonical's Signed `shim` Bootloader:** Microsoft-trusted shim loads the GRUB bootloader.
2. **Canonical's Signed Linux Kernel:** We use the unmodified, upstream Ubuntu LTS kernel.
3. **In-Tree Kernel Modules:** By adopting standard `overlayfs` (for the Live filesystem) and `nftables` (for the Anti-Cheat firewall) instead of third-party patches, the signed kernel never complains about tainted or unsigned modules.

**Advantage:** Contestants can bring their personal Windows 11 laptops (which mandate SecureBoot) to a competition, plug in the provided GallosOS USB, and boot immediately without digging into BIOS security settings.

---

## 2. Hardware Requirements Matrix

Because GallosOS uses an immutable SquashFS + OverlayFS architecture, its memory requirements depend strictly on the boot mode chosen by the organizer.

### 2.1 Standard Boot (Read-Only USB + Ephemeral RAM)

In this mode, the core OS resides compressed on the USB drive (mounted read-only). All system changes, logs, and contestant files are written exclusively to ephemeral RAM (`tmpfs`). **The USB drive is never written to during operation.**

- **Minimum CPU:** 64-bit AMD64 / x86_64 processor (Intel Core 2 Duo / AMD Athlon 64 X2 or newer).
- **Minimum RAM:** 4 GB (Recommended: 8 GB for heavy IDEs like IntelliJ or CLion, as all session data and modified files live in RAM).
- **Storage:** 16 GB+ USB Flash Drive.
  - **Quality & Read Speed Warning:** Organizers **must** use recognized, high-quality brands (e.g., SanDisk, Kingston, Samsung). Cheap promotional USB drives suffer from severe read bottlenecks and thermal throttling, causing the OS to freeze completely when loading heavy IDEs like IntelliJ or CLion into RAM.
  - **USB-C Recommendation:** Whenever possible, use USB-C / USB 3.2 Gen 1 drives. USB-C ports on modern laptops generally offer superior, sustained read bandwidth and avoid legacy USB 2.0 internal hub bottlenecks, drastically reducing IDE loading times.

### 2.2 `toram` Boot (RAM-Resident Disconnected Execution)

GallosOS supports the `toram` boot parameter. During early boot, the entire SquashFS OS image is copied directly into system RAM. The USB drive can then be physically unplugged.

- **Minimum CPU:** 64-bit AMD64 / x86_64 processor.
- **Minimum RAM:** 16 GB. (The OS payload of ~4.5 GB consumes RAM immediately, leaving ~11.5 GB for the desktop, compilers, and IDEs).
- **Design Target:** Eliminates USB NAND read bottlenecks after boot by executing all binary payloads directly from system memory.

---

## 3. Peripheral & Network Compatibility

- **Displays:** Wayland natively supports fractional scaling and multi-monitor setups.
- **Keyboards:** The `gallos.toml` directive automatically provisions the correct keyboard layouts (`latam`, `us`, `es`, `br-abnt2`, `dvorak`), which contestants can toggle instantly via `Super + Space` (or `Alt + Shift`) and the Waybar status bar.

### 3.1 Networking & The Broadcom (`b43` / `wl`) BYOD Dilemma

In BYOD (Bring Your Own Device) competitive programming events (such as university training camps or club meetings), legacy laptops with Broadcom Wi-Fi chips (e.g., BCM4311, BCM4318, BCM4322, BCM4331, BCM4360) present a classic Linux distribution challenge:

1. **The Redistribution Limitation:**
   - While modern Broadcom chips (`brcmfmac`) have legally redistributable firmware included in standard `linux-firmware`, legacy Broadcom cards (`b43` / `wl`) require proprietary microcode that Broadcom's EULA forbids redistributing in public Linux ISO images.
2. **GallosOS Pragmatic Approach for BYOD:**
   - **Open-Source Firmware Inclusion (`openfwwf`):** GallosOS pre-bundles `firmware-b43-openfwwf` (Open Source Firmware for IEEE 802.11 Devices), providing legal out-of-the-box support for basic 802.11b/g Broadcom chips (BCM4306, BCM4311, BCM4318, BCM4320).
   - **Modern Broadcom Support (`brcmfmac`):** Modern 802.11ac/ax chips (BCM4350, BCM4356, etc.) operate out of the box via standard in-tree `linux-firmware`.
   - **Help Desk Operational Fallback (Recommended):** For BYOD events with legacy laptops bearing unsupported Broadcom hardware, organizers should keep a small pool of standard USB Ethernet adapters or USB Wi-Fi dongles (e.g., MediaTek `mt76` / Realtek `rtw88` chipsets, which use in-tree redistributable firmware) at the technical support desk.

---

## 4. Mass Flashing Hardware (`gallos-flash`)

When preparing for a contest, organizers often need to flash 50+ USB drives simultaneously using the `gallos-flash` utility. Writing a 4.5 GB OS image to multiple drives concurrently requires significant electrical power and I/O bandwidth.

To avoid catastrophic write failures or extremely slow flashing times (e.g., 4+ hours), follow these hardware guidelines for your "flashing station":

1. **Externally Powered USB Hubs (Mandatory):** Never use a cheap, unpowered USB hub to flash multiple drives. The combined power draw of writing to 10 USBs simultaneously will exceed a standard motherboard port's power limit, causing drives to disconnect randomly during the flash. Always use an **Active USB 3.0+ Hub with a dedicated AC power adapter** (Recommended brands: Anker, Sabrent, TP-Link).
2. **Dedicated PCIe Expansion Cards (Desktops):** If you are using a desktop PC as a flashing station, the best approach is to install a dedicated PCIe to USB 3.2 expansion card (Recommended brands: StarTech, Inateck, Orico). Unlike external hubs that share a single port's bandwidth, PCIe cards connect directly to the CPU's PCIe lanes, guaranteeing full write speed to every port simultaneously.
3. **Thunderbolt / USB-C Hub Topology (Laptops):** If flashing from a laptop, plug your powered USB hub into a **Thunderbolt 3/4 or USB-C** port rather than a traditional rectangular USB-A port. Thunderbolt ports have massive bandwidth (up to 40 Gbps) compared to standard USB-A (5 Gbps), preventing the hub from becoming a severe data bottleneck when flashing 10+ drives at once.

---

## 5. CPU Execution Determinism & Thermal Throttling Prevention

In competitive programming, contestants rely on accurate local execution timings when benchmarking complex algorithms against maximum test cases ($N = 10^5, 2 \times 10^5$). On modern multi-core laptops, dynamic frequency scaling (Intel Turbo Boost, AMD Core Performance Boost) and thermal throttling introduce non-deterministic execution spikes, causing identical code to take 0.8s on one run and 2.1s on another.

Inspired by proven production practices from the **ICPC World Finals Systems Operations team** ([`icpcsysops/ansible`](./COMPARATIVE_ANALYSIS.md#9-specialized-analysis-icpc-world-finals--nac-sysops-fleet-orchestration-icpcsysopsansible)), GallosOS incorporates declarative hardware stabilization mechanisms:

### 5.1 Dynamic Boost Disabling & Fixed Performance Governor

During `Contest` mode (or declaratively via `[system.hardware]`), `gallos-daemon` configures kernel CPU frequency interfaces:

- **Intel Processors (`intel_pstate`):**

  ```bash
  # Disable dynamic overclocking / boost spikes
  echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo
  # Pin performance bounds to base non-overclocked clock
  echo 100 > /sys/devices/system/cpu/intel_pstate/min_perf_pct
  echo 100 > /sys/devices/system/cpu/intel_pstate/max_perf_pct
  ```

- **AMD Processors (`cpufreq`):**

  ```bash
  # Disable AMD Core Performance Boost
  echo 0 > /sys/devices/system/cpu/cpufreq/boost
  ```

- **Frequency Governor:**
  Sets `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` to `performance`, preventing powersave downclocking transitions during interactive idle pauses between compile runs.

### 5.2 HyperThreading Sibling Thread Isolation & CPU Pinning

On laptops where concurrent background threads or thermal budgets impact single-threaded algorithmic performance:

1. **Virtual Sibling Thread Deactivation:**
   Optionally offlines logical HyperThreading pairs (`echo 0 > /sys/devices/system/cpu/cpu<N>/online`), ensuring contestant processes execute strictly on dedicated physical cores with full L1/L2 cache allocation.
2. **Process Affinity Pinning (`taskset`):**
   GallosOS run-wrapper utilities (`runc`, `runcpp`, `runpython3`, `runjava`, `runkotlin`) support pinning execution to specific isolated physical CPU cores via `taskset -c <core>`, eliminating context switching and scheduler migration jitter.

---

> [!NOTE]
> **Legal Disclaimer:** The hardware brands listed in this document (e.g., SanDisk, Kingston, Samsung, Anker, Sabrent, TP-Link, StarTech, Inateck, Orico) are provided strictly as technical examples of historically reliable equipment for mass-deployment IO scenarios. The GallosOS project is an independent open-source initiative and has no commercial affiliation, partnership, sponsorship, or endorsement agreement with any of these manufacturers.
