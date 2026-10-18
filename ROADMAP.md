# GallosOS Development Roadmap & Feature Tracker

This roadmap groups the implementation work described in `docs/` into seven phases. Phase numbers identify areas of delivery; individual capabilities may land ahead of their phase. Specifications include both current behavior and future designs, so their presence alone does not mark an item complete.

## Implementation and release status

- `[x]` means implementation is complete in the repository for the stated scope.
- `[ ]` means implementation is incomplete or planned. A partial helper or configuration field does not complete the feature that consumes it.
- Implementation completion does not establish booted-image, graphical, or physical hardware acceptance. Those results belong in [Release acceptance](#release-acceptance).

The MVP implementation scope is Phase 1 through Phase 3: the build and boot foundation, security mechanisms, and runtime configuration engine. Stabilization and acceptance remain in progress. Physical hardware and the base graphical contestant session remain acceptance gates before Phase 4; implementing the MVP does not by itself make an image ready for venue deployment. Phases 4–7 add workstation capabilities, Organizer tools, software expansion, release engineering, and venue services.

The selected release core consists of GCC (C/C++), Clang (C/C++), OpenJDK 21 (Java), Python/PyPy, Rust, and Kotlin, with Geany, terminal editors, Firefox, and VSCodium. The neutral ISO uses GallosOS branding, open practice, unrestricted websites, USB storage allowed, and Contest/Event modes disabled. `club.gallos.toml` supplies optional CPC-GALLOS identity; `training.gallos.toml` supplies a public-judge allowlist. Official Contest lockdown requires an Organizer policy. Additional languages, browsers, and IDEs in Phase 6 are future expansion options, not additional initial-release requirements.

---

## Phase 1: Build & Development Foundation (Alpha)

*Goal: Provide the containerized build pipeline, live filesystem, basic desktop provisioning, core packages, and contributor environment.*

- [x] **OCI Build Container:** Bootstrap the Ubuntu 24.04 rootfs in Podman/Docker without installing the build toolchain on the host.
- [x] **Dual Bootloader Chain:** Generate hybrid images with Ubuntu's signed shim/GRUB/kernel chain for UEFI and a GRUB PC-BIOS boot image and hybrid MBR for Legacy BIOS.
- [x] **Casper Live Boot Engine:**
  - [x] Seed the contestant home and expose the approved `GALLOS_BOOT` medium through `/boot/gallos/` using `vendor/inherited/maratona-casper/55gallos-live`.
  - [x] Mount discovered `.gsm` SquashFS layers through the build-time patch to casper's `setup_overlay()` in `vendor/inherited/maratona-casper/casper-gsm-overlay.sh`.
  - [x] Retain upstream casper's `toram` path. Historical QEMU notes reported RAM-copy behavior and composition with a test module; release-candidate verification is tracked separately.
  - [x] Restrict boot-medium configuration discovery to approved local paths. Mode-aware `event-data` mounts belong to Phase 3's host service, rather than casper or the daemon's private mount namespace.
- [x] **SquashFS and Hybrid ISO Packaging:** Package the base rootfs using `mksquashfs -comp zstd` and generate the ISO with the scripts under `build/scripts/`.
- [x] **Basic Wayland Session Provisioning:** Install and configure Labwc, Waybar, Foot, Mako, and the application launcher. This covers session assembly; complete dynamic desktop controls remain in Phase 4.
- [x] **Selected Core Package Provisioning:** Declare the six toolchain families in `build/profiles/universal.build.toml`, provision Firefox and VSCodium in `02-provision.sh`, and record installed versions in `/usr/share/gallos/toolchains.tsv`. Compiler execution, browser workflows, and IDE use still require image acceptance.
- [x] **Developer Environment and Root Tasks:** Provide the devcontainer, root Makefile, Python environment instructions, EditorConfig, Git file attributes, pre-commit hooks, and contribution templates. See [`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md).
- [x] **Repository QA and ISO Boot Workflow:** Define Ruff, pytest, ShellCheck, TOML, and Conventional Commits checks, plus BIOS/UEFI/Secure Boot/`toram` and modified-kernel rejection steps in `.github/workflows/iso-boot.yml`. Workflow implementation does not establish a successful run for a particular release image.

---

## Phase 2: Security Enforcement & Resource Protection (Beta 1)

*Goal: Implement policy-scoped network and device restrictions, privilege controls, and resource protection while preserving the neutral practice baseline.*

- [x] **Restricted-Mode Network Enforcement:**
  - Render `nftables` filtering for restricted policies, including Judge Server IP/CIDR allowlists and restricted outbound traffic.
  - Disable IPv6 through the kernel boot parameter and sysctl fallback.
  - Use the local proxy for named-host Default/Event training allowlists and block direct workstation egress under those policies. Keep neutral Default browsing open.
- [x] **Peripheral and USB Policy Helpers:** Apply contestant `polkit`/`udisks2` restrictions and host-service storage enforcement. Preserve the live medium and HID interfaces while restricting other storage according to policy. Physical and live-image enforcement remain acceptance items.
- [x] **TTY and Privilege Hardening:** Disable ordinary VT switching, remove `sudo`, and keep the built root password locked by default.
- [x] **Organizer Root Recovery and GRUB Authentication:** Support an explicitly configured local recovery password through `gallos-root-access.service` and require a build-supplied GRUB PBKDF2 credential for menu editing and the GRUB command line. Normal boot does not require that GRUB password. See [`docs/ROOT_ACCESS.md`](./docs/ROOT_ACCESS.md).
- [x] **EarlyOOM Guard:** Enable `earlyoom -n`, configure process avoidance/preference patterns, and set `OOMScoreAdjust=-900` on `gallosd.service`. These reduce risk; they do not guarantee process immunity. The desktop notification bridge remains a Phase 4 item.
- [ ] **Restricted-Profile Anti-AI Website and Search Policy:** Design and implement effective handling of AI endpoints, embedded search answers, and web relays, including Google Translate website translation, CroxyProxy, and Startpage Anonymous View. Preserve the neutral fallback. Domain lists alone do not establish enforcement.

---

## Phase 3: Runtime Configuration, Modes & Storage (Beta 2)

*Goal: Implement the daemon, trusted configuration, mode scheduling, workspace transitions, and machine identity.*

- [x] **`gallosd` Core Engine:** Run the Python daemon as `gallosd.service`, parse TOML, validate runtime directives against `schema/directives.schema.json`, and install `/usr/bin/gallosctl`. Read-only diagnostics are available to unprivileged users; mutating IPC commands require root.
- [x] **Trusted Local Configuration:** Load the root-only `/etc/gallos/gallos.toml` override, approved boot-medium policies, and the ISO baseline in priority order. Reject policy selection through kernel arguments, DHCP options, arbitrary runtime URLs, or unrelated attached disks.
- [x] **Build-Trusted Remote Organizer Policy Updates:** A custom ISO can embed one HTTPS source URL through `REMOTE_POLICY_URL`. Fetch on startup and every five minutes, validate responses, and replace only the bundled baseline. Keep explicit local policies above remote updates and retain the current-boot last-known-good response under `/run/gallos`. The official neutral ISO has no remote source. This implemented capability is grouped here rather than under the future Venue Controller. See [`docs/CONFIG_SPEC.md`](./docs/CONFIG_SPEC.md#2-configuration-delivery-methods).
- [x] **3-Tier Mode Scheduling:** Evaluate configured Contest/Event absolute windows and monotonic automatic/manual Contest durations, then invoke policy operations at mode transitions. The runtime does not inspect NTP synchronization state.
- [ ] **Clock-Confidence Handling:** Detect whether the system clock is synchronized, define safe behavior when absolute schedule time is untrusted, and expose clock confidence to the Organizer. The current scheduler evaluates absolute windows without this check.
- [x] **Hot Reload and Transition Hooks:** Reload valid Organizer policy without rebooting and request firewall, browser policy, wallpaper, and desktop state updates. Graphical display of that state still needs the Phase 4 UI integration below.
- [x] **Host Event Storage and Clean State Transitions:** Use `gallos-event-storage.service` to mount optional `event-data` in the host namespace outside Contest. Stop contestant activity and invoke host cleanup helpers before a fresh Contest; fail closed on policy or cleanup errors. Keep the kiosk stopped and expose the configured local root recovery console when a transition fails.
- [x] **Post-Contest Storage Restoration:** Reapply open-mode USB policy and restore the optional Event workspace when leaving Contest. Visible export guidance and end-to-end contestant workflows remain acceptance work.
- [x] **Machine Identity:** Load per-workstation `machine.toml` data and apply hostname/team identity. DHCP reservations and Venue Controller assignment depend on venue infrastructure and are not supplied by this feature.

Historical stabilization notes report a signed Live-image QEMU run covering host-visible event storage, configured root login, busy-mount failure recovery, manual retry into Contest, return to Default, and preserved Event data. Earlier daemon-private mount handling was replaced by the host service. These reports describe earlier runs; acceptance of a release candidate requires the image identity and corresponding evidence below.

---

## Phase 4: Contestant Workstation Features (Beta 3)

*Goal: Complete desktop controls, printing, branding, and offline references after the base-session acceptance gates.*

- [ ] **Dynamic Desktop Controls:** Connect the visible mode badge and countdown to daemon state, complete mode-aware application-menu behavior, and implement the specified clock-confidence and low-memory indicators. The generated bar currently includes placeholder mode/countdown text; its presence is not completed runtime integration.
- [ ] **Keyboard Layout Switcher:** Apply Organizer-configured XKB layouts in the compositor and expose the active layout and switching control in Waybar. The current `gallos-layout-toggle` helper only cycles a file and sends a notification; its shortcuts do not change the actual layout.
- [ ] **EarlyOOM Desktop Notifications:** Install and start a contestant-session bridge such as `systembus-notify`, and integrate effective low-memory notifications with Mako. `earlyoom -n` alone does not complete this feature.
- [ ] **Mode-Aware Audio:** Connect the specified `allow_audio` policy to effective PipeWire/WirePlumber session controls; a configuration field alone does not apply mute or disable behavior.
- [ ] **`gallos-print` CUPS Subsystem:**
  - Implement contestant printing based on the `printfile` (`a2ps` / `enscript`) pattern from `icpcsysops/ansible` and SWERC Lyon.
  - Support browser/judge printing through the default virtual CUPS queue and screenshot printouts via `grim` (`gallos-print --screenshot`).
  - Implement syntax highlighting, line numbering, team metadata, timestamps, and page numbers through `gallos-cups-filter`.
  - Enforce Organizer printer allowlists.
- [ ] **Rapid White-Labeling and Branding Engine:**
  - Generate an offline Plymouth splash from `boot_splash_logo_url` and inject configured desktop themes/wallpapers with optional `show_powered_by_gallos` watermark.
  - Add a GRUB background and menu colors as the initial branding increment; a full icon-based `theme.txt` is a later extension.
  - Review Canonical's trademark/branding policy before changing Ubuntu release-identification fields.
  - Follow [`docs/BOOT_BRANDING.md`](./docs/BOOT_BRANDING.md); existing asset directories are scaffolding.
- [ ] **Offline Documentation and Translation:** Bundle static C++, Python, and Java references with browser bookmarks. Candidate packages include `cppreference-doc-en-html`, `python3-doc`, and `openjdk-21-doc`; verify package availability when implementing. Evaluate GoldenDict or stardict with EN-ES / EN-PT data for the offline dictionary.
- [ ] **Optional Proprietary GPU Driver Support:** Package `drivers/nvidia-proprietary` as a DKMS-carrying `.gsm` module, implement persistent MOK signing keys in the builder, and document per-machine enrollment. A future CUDA toolchain would depend on this driver work and is not yet scoped.

---

## Phase 5: Organizer Tooling Suite (RC 1)

*Goal: Build standalone Organizer utilities for USB preparation, migration, and visual configuration.*

- [ ] **`gallos-convert` (HuronOS Migration CLI):** Convert legacy `.hdf` into canonical `gallos.toml`, with `--validate` and `--diff` support.
- [ ] **`gallos-flash` (Mass Multi-USB Flasher):**
  - Implement a concurrent writer targeting 50+ drives, with Linux, macOS, and Windows WSL2 workflows. This is a target, not a measured throughput or concurrency result.
  - Create FAT32 `GALLOS_BOOT` and an ext4 `event-data` partition using the remaining drive capacity when Event persistence is selected, without a persistent Contest partition.
  - Provide an unattended CLI and avoid shared global mount points or system-wide mutable state between flashing instances.
- [ ] **`gallos-inject` (In-Place USB Updater):**
  - Preserve partition tables and boot sectors while replacing configuration and branding on `GALLOS_BOOT`.
  - Add/remove standalone `.gsm` modules and selectively rebuild the top `99-custom.gsm` override layer with checksum updates.
  - Support in-place GRUB parameter updates and concurrent batch updates of mounted GallosOS drives.
  - Retain the four customization tiers described in [`docs/BUILD_SYSTEM.md` §5](./docs/BUILD_SYSTEM.md#5-in-place-usb-delta-updates-and-layer-injection-gallos-inject).
- [ ] **GallosOS Config Builder:** Provide an Angular web application with schedule editing, module selection, firewall allowlists, and TOML preview/download, hosted locally or on GitHub Pages.

---

## Phase 6: Software Expansion & Release Engineering (GA Release)

*Goal: Expand the selected core through optional software and platform support, and automate release delivery.*

- [ ] **Optional Toolchains and Software Modules:** Evaluate and package additional runtimes such as Mono/.NET, using the upstream contest manifests as references. Build real `.gsm` bundles and wire build-profile module copying into ISO assembly; the existing casper mount mechanism alone does not supply module packages.
- [ ] **Additional Browsers:** Evaluate Chromium and GNOME Web alongside the Firefox baseline. Require offline launch, effective policy/telemetry configuration, printing, and graphical acceptance before advertising a browser as supported.
- [ ] **Expanded IDE Catalog and Offline Extensions:** Evaluate JetBrains IDEs (IntelliJ IDEA, PyCharm, CLion), Code::Blocks, KDevelop, Neovim/LazyVim, Kate, and Zed beyond the selected Geany/VSCodium/terminal-editor baseline. Design offline extension bundles with correct IDs and OverlayFS permissions; review licensing, AI controls, telemetry, and offline operation before inclusion.
- [ ] **Optional IDE AI-Plugin Purging:** Implement startup removal of unwanted AI assistants for expanded IDE packages. Preserve and verify the telemetry settings already generated for the selected applications; broader restricted-profile web policy remains in Phase 2.
- [ ] **Additional `base_os` and Kernel Pairings:** Define supported release tiers and verify alternate Ubuntu bases and their kernel/HWE pairings. Ubuntu 24.04 remains the current build target; other pairs are not validated defaults.
- [ ] **University Exam Workstation Evaluation:** Evaluate Organizer LMS allowlisting, browser-only kiosk behavior, and the community [SEB for Linux](https://github.com/Jvr2022/seb-linux) project. `examples/exam.gallos.toml` already supplies a Moodle public-demo policy example; production LMS/SSO integration and secure exam behavior remain unimplemented/unverified.
- [ ] **VM Appliances and Guest Integration:** Automate `.ova` packaging for VirtualBox/VMware and `.qcow2` packaging for KVM/QEMU. Guest-tool packages are declared in the core recipe, but mode-aware services, display integration, and supported-hypervisor behavior require implementation and acceptance as applicable.
- [ ] **Public Documentation Site:** Publish user and architectural documentation through an official site, evaluating Docusaurus or GitBook.
- [ ] **Release Automation and Extended Acceptance Harnesses:** Build and publish release ISOs on Git tags and extend guest checks to verify firewall and daemon behavior. Reuse Phase 1's existing QA and firmware boot workflow instead of treating them as future work. Tie release results to the exact image checksum and source revision.

---

## Phase 7: Venue Services & Auditing (Post-GA / v2.0)

*Goal: Provide optional venue infrastructure, fleet monitoring, and auditing without requiring it for standalone workstations.*

- [ ] **Venue Controller Server Mode:** Provide optional DHCP, NTP, machine assignment, monitoring, printing coordination, and audit aggregation. The separate Judge Server remains external.
- [ ] **Signed Clarification Broadcast:** Implement the optional Venue Controller signer and workstation client described by the `gallos-broadcast` configuration. Keep it disabled by default and independent from Judge Server clarification workflows.
- [ ] **Administrative Proctoring and Input Forensics:** Evaluate the `martkeys` architecture from `icpcsysops/ansible`, with explicit Organizer policy through `enable_keystroke_forensics` for input metrics/keystroke collection. Implement authorized screenshots through a privileged Wayland capture interface and `node-exporter` / `gallos-exporter` fleet metrics.
- [ ] **Audit Export:** Implement `gallos-audit-export` to aggregate workstation logs, OOM events, firewall drops, input metrics, print history, and proctoring evidence into a `gallos-audit-YYYYMMDD.tar.gz` archive.
- [ ] **ARM64 Exploration:** Evaluate AArch64 Live builds for Apple Silicon through the Asahi boot stack and Qualcomm Snapdragon laptops with suitable UEFI firmware. Keep 32-bit x86 outside the supported architecture scope. These are research targets, not tested hardware support.

---

## Release acceptance

Acceptance results are separate from implementation checkboxes. Use **PASS**, **FAIL**, **BLOCKED**, or **NOT TESTED** for each identified run. Every PASS or FAIL must name the source revision, ISO SHA256, environment, exact check, and evidence location. Record prerequisite failures as BLOCKED and checks that were not run as NOT TESTED. A repository check or an implemented CI workflow cannot substitute for a live-image result.

The table below tracks open gates for the next release candidate. No candidate checksum or linked runtime report is recorded here yet; previous QEMU observations above remain historical context and are not carried forward as fresh PASS results. Populate the candidate identity and evidence when those checks are performed. Repository lint/unit results are reported with each change and do not close these gates.

| Gate | Relevant phase | Status | Evidence needed |
| :--- | :--- | :--- | :--- |
| BIOS/UEFI boot, enforced Secure Boot, `toram`, and modified-kernel rejection | 1–2 | NOT TESTED | Candidate checksum, firmware configuration, and guest/boot logs; reuse `iso-boot.yml` checks. |
| Host-visible Event storage, busy-mount failure/retry, return from Contest, and preserved data | 3 | NOT TESTED | Candidate checksum and host/guest state evidence for the complete transition sequence. |
| Whole-workstation network restrictions, USB storage/HID handling, root-only mutation, and clean Contest state | 2–3 | NOT TESTED | Direct enforcement results, unchanged state after denied operations, and live-medium/device evidence. |
| Base contestant desktop, application launch, configured graphics, and visible mode information | 1–3 | NOT TESTED | An actual contestant graphical session with screenshots and expected-state assertions. |
| Selected compilers, Firefox, Geany/VSCodium, public-judge workflows, and restricted training proxy | 1–3 | NOT TESTED | Installed version inventory, compile/run results, browser login/submission, policy, and graphical evidence. |
| Keyboard switching and the remaining specified Waybar controls | 4 | BLOCKED | Complete compositor layout application and UI integration before acceptance. |
| Physical venue hardware, firmware, peripherals, and workstation behavior | 1–3 | NOT TESTED | Per-machine results; VM observations do not certify physical hardware. |

This table makes no claim that hardware benchmarking, physical lab trials, or a release-candidate acceptance run has occurred.
