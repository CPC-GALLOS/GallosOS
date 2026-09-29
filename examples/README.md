# GallosOS Directives Profiles (`examples/`)

This directory contains example profiles for the canonical **`gallos.toml`** directives format. Organizers must validate judge access, language versions, and desktop behavior before an official event.

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
3. **`examples/*.gallos.toml` (Example Profiles):**
   - Pre-configured blueprints for popular competitive programming platforms.
   - **How to use:** Pick the template that matches your contest, customize your timestamps, and deploy!
   - **Automatic Discovery:** If one profile is placed in an approved local config directory without `gallos.toml`, `gallosd` loads it ahead of the ISO baseline. For predictable deployment, organizers should copy the chosen profile as `gallos.toml` to the approved boot-medium config directory.
   - **Multiple Profiles:** Kernel boot arguments do not select policy. Copy the profile needed for the event to the approved boot medium as `gallos.toml` before boot.

---

## ⚙️ Why are all blueprints `*.gallos.toml`? (Build-Time vs. Run-Time)

A common point of confusion for new users is why this directory contains only runtime directives (`*.gallos.toml`) and no build manifests (`*.build.toml`):

- **Build-Time Recipes (`build/profiles/*.build.toml`):** Used strictly during ISO compilation by developers running the containerized build pipeline (`gallos-builder`). The repository maintains its canonical base build recipe at [`build/profiles/universal.build.toml`](../build/profiles/universal.build.toml); see [`build/profiles/README.md`](../build/profiles/README.md) and [`docs/BUILD_SYSTEM.md`](../docs/BUILD_SYSTEM.md).
- **Run-Time Directives (`examples/*.gallos.toml`):** Blueprints in this directory are intended for **contest organizers**. Organizers do not compile custom OS images from scratch; they simply flash the official release ISO and supply one of these blueprints at runtime.
- **The "Single Universal Base ISO" Principle:** The underlying base system (Ubuntu 24.04 LTS minimal, Linux kernel, Wayland kiosk stack, audio, and device management) is identical across all competitions. **A single ISO built with `universal.build.toml` runs every single contest archetype listed below.** All contest-specific constraints — judge IP whitelists, allowed IDEs, countdown clocks, and desktop lockouts — are evaluated dynamically at boot time by `gallosd`.

---

## 📁 Event Archetypes & Operational Use Cases

Each configuration profile in this directory demonstrates a distinct **real-world competitive programming use case**, showcasing the versatility and security features of GallosOS:

The older contest examples include requested `software` module identifiers and
version descriptions. Those entries do not install packages: `.gsm` module
activation remains future work. Check `/usr/share/gallos/toolchains.tsv` in a
built ISO for the toolchains actually present.

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

- [**`neutral.gallos.toml`**](./neutral.gallos.toml) — the GallosOS-branded ISO fallback for open practice and informal public-judge contests.
- [**`club.gallos.toml`**](./club.gallos.toml) — CPC-GALLOS club identity and open internet access, with no expiring schedule.
- [**`training.gallos.toml`**](./training.gallos.toml) — restricted multi-judge practice, including the Codeforces main site, `m1`, `m2`, `m3`, and `mirror` hosts. The list contains hosts whose pages or problem catalogs could be confirmed at review time; unavailable or unconfirmed legacy links are excluded pending a new check. Judge login, assets, and submissions require graphical acceptance before release.

The training profile restricts the whole workstation through a local proxy and outbound firewall. An Event window inherits the Default site list unless it explicitly overrides it. Search engines and general GitHub access are not on this allowlist. AI features hosted within an allowed judge are a separate policy question. See the [judge review](../docs/TRAINING_JUDGES.md) for inclusion limits and excluded links.

---

### 3. 🛡️ Proctored Remote Examinations & Online Qualifiers (Anti-Cheat Kiosk)

- [**`icpc-online-exam.gallos.toml`**](./icpc-online-exam.gallos.toml) — **Remote Preliminary Round & Online Assessment**
  - **Operational Context:** Remote contestants taking an online qualifier or hiring assessment from home or unmonitored labs.
  - **Network & Security:** Strict single-purpose exam lockdown (CodeChef Exam Mode); blocks all external LLMs, AI endpoints, and communication tools.
  - **Auditing:** Scheduled background desktop screenshots and fleet telemetry streaming.
  - **Printing:** Disabled (`mode = "none"`).

### 4. 🏫 University Exam Workstations (Moodle Policy Example)

- [**`exam.gallos.toml`**](./exam.gallos.toml) — a restrictive Contest-mode profile for testing LMS allowlisting against Moodle's public demo host. It is a policy example only and must not be used for a live exam; institutions need to identify and test their own LMS, SSO, and supporting service hosts.
- **Lockdown options:** GallosOS browser-only kiosk controls and the third-party [SEB for Linux](https://github.com/Jvr2022/seb-linux) client are separate options to evaluate. The community SEB project is an experimental compatibility candidate; GallosOS integration, secure lockdown behavior, and Moodle/Canvas compatibility have not been verified.
- **Assessment policy:** Google Scholar and other external reference sites are excluded from the sample allowlist. Organizers should explicitly allow each resource only when the exam rules permit it.

---

### 5. 🏫 School & Regional Informatics Olympiads (Bilingual & Accessible)

- [**`omegaup-omi.gallos.toml`**](./omegaup-omi.gallos.toml) — **National Informatics Olympiad (OMI / omegaUp)**
  - **Operational Context:** High school and junior olympiads (Olimpiada Mexicana de Informática).
  - **Network & Security:** Whitelists omegaUp grader endpoints, CDNs, and official committee portals.
  - **Printing:** Venue Controller hosted print spooler (`mode = "hosted"`).
  - **Toolchain:** GCC, Python 3, Java, beginner-friendly text editors (Geany, VSCodium), and offline Spanish documentation.

---

## 🚀 Deployment & Configuration Precedence

GallosOS currently reads policy from trusted local TOML sources.

The root-only `/etc/gallos/gallos.toml` emergency override takes precedence over a canonical `gallos.toml` on the approved boot medium, one unambiguous named profile, and the ISO baseline. Kernel arguments, DHCP options, remote URLs, and arbitrary attached disks do not supply policy.

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

Before an event, copy the selected profile to the approved boot medium as `gallos.toml`. If an authorized Organizer needs a last-minute correction during Contest, edit `/etc/gallos/gallos.toml` and run `gallosctl reload`. The existing controller reports parse errors and retains the active policy when reload fails.

### 3. Visual Authoring (`GallosOS Config Builder`)

The planned GallosOS Config Builder can load a blueprint to adjust time windows and policy visually, then export a local `gallos.toml` for review and deployment.
