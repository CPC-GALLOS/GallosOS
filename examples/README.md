# GallosOS Directives Profiles (`examples/`)

This directory contains production-ready configuration blueprints for the canonical **`gallos.toml`** directives format.

---

## 🧭 `gallos.toml` vs. `machine.toml` vs. `examples/*.gallos.toml`

To keep deployment modular and easy to manage, GallosOS separates configuration into three clean roles using standardized compound extensions:

1. **`gallos.toml` (Global Contest Policy — WHAT & WHEN):**
   - The master configuration file governing the **entire competition**.
   - It is **identical across all 50–200 machines** in the arena.
   - Defines: schedule windows, judge whitelist (`allowed_websites`), permitted compilers & IDEs, printing mode (`hosted`, `external`, `none`), wallpapers, and countdown timers.
2. **`machine.toml` (Local Station Identity — WHO & WHERE):**
   - Unique to each physical workstation / USB drive.
   - Defines: `pc_name = "PC-14"`, `room = "Lab-A"`, `team_name = "Team-42"`, and `seat_label = "Desk 03"`.
   - Injected per-USB automatically by `gallos-flash` during mass writing or assigned dynamically via MAC matching by the **Venue Controller**.
3. **`examples/*.gallos.toml` (Production-Ready Blueprints):**
   - Pre-configured blueprints for popular competitive programming platforms.
   - **How to use:** Pick the template that matches your contest, customize your timestamps, and deploy!
   - **Automatic Discovery:** If you place a single profile (e.g. `codeforces-training.gallos.toml`) on a Live USB or Ventoy partition without an organizer's `gallos.toml`, `gallos-daemon` loads it ahead of the ISO's bundled baseline without requiring manual renaming.
   - **Multi-Profile Selection:** If you keep multiple profiles on the same USB (e.g. Day 1 warmup vs Day 2 finals), select between them via the GRUB boot menu parameter `gallos.config=<profile-name>` (e.g. `gallos.config=codeforces-training`).

---

## ⚙️ Why are all blueprints `*.gallos.toml`? (Build-Time vs. Run-Time)

A common point of confusion for new users is why this directory contains only runtime directives (`*.gallos.toml`) and no build manifests (`*.build.toml`):

- **Build-Time Recipes (`build/profiles/*.build.toml`):** Used strictly during ISO compilation by developers running the containerized build pipeline (`gallos-builder`). The repository maintains its canonical base build recipe at [`build/profiles/universal.build.toml`](../build/profiles/universal.build.toml); see [`build/profiles/README.md`](../build/profiles/README.md) and [`docs/BUILD_SYSTEM.md`](../docs/BUILD_SYSTEM.md).
- **Run-Time Directives (`examples/*.gallos.toml`):** Blueprints in this directory are intended for **contest organizers**. Organizers do not compile custom OS images from scratch; they simply flash the official release ISO and supply one of these blueprints at runtime.
- **The "Single Universal Base ISO" Principle:** The underlying base system (Ubuntu 24.04 LTS minimal, Linux kernel, Wayland kiosk stack, audio, and device management) is identical across all competitions. **A single ISO built with `universal.build.toml` runs every single contest archetype listed below.** All contest-specific constraints — judge IP whitelists, allowed IDEs, countdown clocks, and desktop lockouts — are evaluated dynamically at boot time by `gallos-daemon`.

---

## 📁 Event Archetypes & Operational Use Cases

Each configuration profile in this directory demonstrates a distinct **real-world competitive programming use case**, showcasing the versatility and security features of GallosOS:

### 1. 🏆 In-Person Sanctioned Tournaments (Strict Arena Lockdown)

- [**`icpc-onsite.gallos.toml`**](./icpc-onsite.gallos.toml) — **Collegiate Regional Championship (ICPC / DOMjudge / BOCA)**
  - **Operational Context:** 3 contestants per team sharing 1 workstation for a strict 5-hour window.
  - **Network & Security:** Default-DROP firewall permitting only judge and scoreboard IPs; USB mass storage disabled.
  - **Printing:** External arena CUPS server (`mode = "external"`) with automated team metadata header injection (`[GallosOS Print] Team-42`).
  - **Toolchain:** GCC 14.2.0, OpenJDK 21, PyPy3, Kotlin 1.9, VSCodium, CLion, Geany, Neovim, and offline DevDocs.

- [**`maratona-sbc.gallos.toml`**](./maratona-sbc.gallos.toml) — **Latin American Multi-Site Championship (Maratona SBC / BOCA)**
  - **Operational Context:** Official Brazilian & South American ICPC regional final.
  - **Network & Security:** Strict BOCA judge whitelisting (`boca.sbc.org.br`), Portuguese/ABNT2 (`br`) default keyboard layout.
  - **Printing:** Venue Controller hosted print spooler (`mode = "hosted"`), targeted via its static IP by default (mDNS discovery is opt-in only — see `docs/ANTI_CHEAT_AND_SECURITY.md` §3.1).
  - **Toolchain:** Parity with SBC contest rules (GCC 14, Java 21, Python 3.12, PyPy3, Byobu terminal multiplexer).

- [**`ioi-cms.gallos.toml`**](./ioi-cms.gallos.toml) — **International Secondary School Olympiad (IOI / CMS)**
  - **Operational Context:** 1 contestant per workstation, two 5-hour competition days.
  - **Network & Security:** Air-gapped LAN connecting to a local CMS (Contest Management System) server; full root-isolated Wayland kiosk.
  - **Printing:** Arena hall printing queue (`mode = "external"`) for task statements and submitted code review.
  - **Toolchain:** Modern C++ (C++20/C++23 via GCC 14), Python 3.12, Geany, VSCodium, and offline cppreference.

---

### 2. 🎓 Multi-Day Training Camps & Daily Upsolving (Flexible Time Cycles)

- [**`codeforces-training.gallos.toml`**](./codeforces-training.gallos.toml) — **Summer/Winter Camps & University Club Practice**
  - **Operational Context:** Multi-day intensive training (e.g., TCMX, ICPC training camps, university labs).
  - **Automated Time Cycle:** Morning lectures/practice $\to$ afternoon virtual contest simulation $\to$ evening upsolving.
  - **Network & Security:** Whitelist for major public practice platforms (Codeforces, AtCoder, CSES, Kattis, VJudge, GitHub).
  - **Printing:** Disabled (`mode = "none"`).
  - **Toolchain:** Extended language suite (GCC, Clang 18, Rust 1.75+, Python, Java, Kotlin) + CPH (Competitive Programmer Helper) extension for rapid testcase parsing.

---

### 3. 🛡️ Proctored Remote Examinations & Online Qualifiers (Anti-Cheat Kiosk)

- [**`icpc-online-exam.gallos.toml`**](./icpc-online-exam.gallos.toml) — **Remote Preliminary Round & Online Assessment**
  - **Operational Context:** Remote contestants taking an online qualifier or hiring assessment from home or unmonitored labs.
  - **Network & Security:** Strict single-purpose exam lockdown (CodeChef Exam Mode); blocks all external LLMs, AI endpoints, and communication tools.
  - **Auditing:** Scheduled background desktop screenshots and fleet telemetry streaming.
  - **Printing:** Disabled (`mode = "none"`).

---

### 4. 🏫 School & Regional Informatics Olympiads (Bilingual & Accessible)

- [**`omegaup-omi.gallos.toml`**](./omegaup-omi.gallos.toml) — **National Informatics Olympiad (OMI / omegaUp)**
  - **Operational Context:** High school and junior olympiads (Olimpiada Mexicana de Informática).
  - **Network & Security:** Whitelists omegaUp grader endpoints, CDNs, and official committee portals.
  - **Printing:** Venue Controller hosted print spooler (`mode = "hosted"`).
  - **Toolchain:** GCC, Python 3, Java, beginner-friendly text editors (Geany, VSCodium), and offline Spanish documentation.

---

## 🚀 Deployment & Configuration Precedence

GallosOS uses an intelligent **two-tier configuration model** (Baked-In Base + Dynamic Remote Override) that eliminates manual file editing:

### 1. Baked-In Offline Base (`gallos-flash`) — *The Offline Baseline & Fallback*

When preparing physical drives, **`gallos-flash`** burns the ISO to multiple USBs concurrently and bakes in the selected configuration profile, team metadata (`machine.toml`), and branding.

- **Air-Gapped Operation:** If the machine has no internet or the central server is unreachable, GallosOS boots instantly using this baked-in profile.
- **Automated Provisioning:** No manual partition mounting or copying files.

```bash
# Flash 10 USBs concurrently with the baked-in ICPC profile and sequential PC numbers
gallos-flash --image gallos-os-amd64.iso \
             --profile examples/icpc-onsite.gallos.toml \
             --drives /dev/sd[b-k] \
             --room "Lab-A" \
             --prefix "PC-"
```

### 2. Dynamic Remote Override (`gallos.config`) — *Live On-The-Fly Updates*

- Simply point the bootloader to a remote URL (e.g. via GRUB boot parameter `gallos.config=https://...`, DHCP option 235, or `/etc/gallos/sync-server.conf`):

  ```text
  gallos.config=https://gist.githubusercontent.com/.../raw/gallos.toml
  ```

- **Precedence Rule:** At boot, GallosOS checks the remote URL. If available, the **remote directives take precedence and dynamically override the baked-in profile**.
- **Automatic Fallback:** If the network goes down or the URL times out (5-second safety limit), GallosOS automatically falls back to the **baked-in baseline** created during flashing or discovered on local storage.

### 3. Visual Authoring (`GallosOS Config Builder`)

Organizers can load any blueprint into the **GallosOS Config Builder** (Angular Web App) to adjust time windows, firewall rules, and branding visually, then export the resulting `gallos.toml` to a GitHub Gist or feed it directly into `gallos-flash`.
