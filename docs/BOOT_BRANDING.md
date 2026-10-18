# GallosOS Boot Branding Design (Plymouth + GRUB)

**Status:** Design only — not yet implemented. Targets ROADMAP Phase 4 ("Contestant Workstation Features"). Source scaffolding does not complete the branding pipeline; acceptance is tracked separately in [`ROADMAP.md`](../ROADMAP.md#release-acceptance).

## Context

GallosOS's generated boot assets use the GallosOS menu label and custom desktop wallpapers, while the ISO is assembled with `xorriso`. The two branding gaps this design addresses are:

1. **The Plymouth boot splash**, which currently uses the stock `plymouth-theme-ubuntu-text` theme (says "Ubuntu" during boot).
2. **The GRUB boot menu**, which has correct GallosOS text but no visual styling at all (no background image, default GRUB gray-on-black colors).

The motivating goal, per the maintainer: this is *not* about visually cloning huronOS (huronOS's actual boot mechanism is Syslinux/`vesamenu.c32`, not Plymouth or GRUB at all — no source assets or license survive in the local `HuronOS/` reference tree to port, confirmed by a full-tree search turning up zero `grub`/`plymouth` files there). The goal is for GallosOS to *read as a complete, deliberately-designed OS in its own right* rather than a visibly-reskinned Ubuntu — removing Ubuntu's own branding wherever that's technically and legally clean to do, and replacing it with GallosOS's own.

This document is the design for closing that gap. It is deliberately **not** an implementation plan — per the maintainer, Phase 4 hasn't started yet. This spec exists so that when it does, the design work doesn't have to be redone from scratch, and so the newly-created `build/assets/branding/` folder has a clear contract for what belongs in it.

## Goals

- Replace the Plymouth boot splash with a GallosOS-branded theme (dark background, organizer/default logo, simple progress indicator).
- Give the GRUB boot menu a matching dark background and menu color scheme.
- Inventory every place stock Ubuntu branding is currently visible to a contestant, and propose (not finalize) a treatment for each.
- Define where the source assets for both of the above live in the repo, and what the build pipeline is expected to do with them.

## Non-goals

- **Not** visually recreating huronOS's boot screen (ferret mascot, wordmark, isolinux menu style) — no source assets or license exist for that, and it isn't the actual goal (see Context).
- A full GRUB `theme.txt` with per-entry selection icons is deferred beyond the initial branding increment. `build-iso.sh` currently generates normal and `toram` entries; the agreed initial design remains a background image and menu colors.
- **Not** a final legal/trademark determination on removing "Ubuntu" strings from `/etc/os-release` — flagged as an open question requiring verification against Canonical's actual trademark/branding policy before implementation, not asserted here.
- **Not** implementation. No `build/scripts/*.sh` changes, no schema changes, and no real asset files (only placeholder `README.md`s) are part of this pass.

## Current state (verified against the actual pipeline, not assumed)

- `build/scripts/02-provision.sh` (Stage 2, runs inside the chroot) installs `plymouth` and `plymouth-theme-ubuntu-text` via `apt-get` and runs `update-initramfs -c -k all` immediately afterward — i.e. *before* any custom theme would exist. A theme added later in the same stage (or in Stage 3/4, while the chroot mount is still shared) needs its own `update-initramfs -u` call, or it silently won't be in the initrd that `build-squashfs.sh` (Stage 5a) later copies out via a plain `cp`.
- `build/scripts/build-iso.sh` (Stage 5b) generates `grub.cfg` with normal and `toram` entries, a five-second timeout, and authenticated editing/command-line access. It constructs BIOS/EFI boot assets and assembles the final image with `xorriso`; custom theme/background generation is not wired in.
- The `gallos-builder` container image (`build/Containerfile`) already has `grub-pc-bin`, `grub-efi-amd64-bin`, `grub-efi-amd64-signed`, `shim-signed`, `grub-common`, and `xorriso` — sufficient for GRUB theming. It does **not** have any Plymouth theme-authoring/preview tooling (not needed at build time; Plymouth themes are just files copied into the chroot).
- `schema/directives.schema.json` already defines `[branding]` with `name`, `organizer`, `logo_url`, `boot_splash_logo_url`, `show_powered_by_gallos` (`additionalProperties: false` — no other keys accepted today). `docs/CONFIG_SPEC.md` already states the boot splash logo can only ever be baked-in (Method B), never fetched remotely, because there's no network in the first seconds of boot.
- `DIRECTIVES_PROFILE` already selects the bundled runtime fallback for a custom ISO. The missing work is consuming the selected policy's branding assets to generate and embed boot themes, not choosing which policy to bundle.
- `build/assets/branding/` now contains documentation scaffolding for the planned Plymouth and GRUB assets; it does not contain a completed theme or pipeline consumer.

## Design

### 1. Plymouth theme

A new theme named `gallos`, using Plymouth's `script` plugin (the same plugin family as Ubuntu's own default themes — well-documented, no per-frame PNG sequence required, positions elements relative to `Window.GetWidth()/GetHeight()` so it isn't tied to one resolution).

- **Files** (destined for `build/assets/branding/plymouth/`, see that folder's `README.md`): `gallos.plymouth` (theme descriptor), `gallos.script` (the actual script: solid `#1e1e2e` background — the same dark navy already used for the desktop wallpaper and Waybar in `02-provision.sh`, for visual continuity from boot splash straight into the desktop — a centered logo, and a simple pulsing-dots progress indicator).
- **Logo source:** the organizer's `[branding].boot_splash_logo_url` when the build is a baked-in (Method B) Track 2 build; a bundled default GallosOS wordmark otherwise. *(Whether that default is hand-authored artwork or generated programmatically — following the same stdlib `zlib`/`struct` flat-PNG pattern `02-provision.sh` already uses for the desktop wallpapers, so no binary asset needs to be committed to git — is an open decision, deliberately left unresolved here; see "Open questions" below.)*
- **Pipeline change (Stage 2, `02-provision.sh`):** copy the theme files into `$ROOTFS/usr/share/plymouth/themes/gallos/`, run `plymouth-set-default-theme -R gallos` inside the chroot, and add the missing `update-initramfs -u` call immediately after (the existing `update-initramfs -c -k all` earlier in the script runs too early to pick this up). As part of de-branding, drop `plymouth-theme-ubuntu-text` from the `apt-get install` line once `gallos` is the default — it's dead weight if nothing ever selects it.
- **`show_powered_by_gallos`:** when true, render a small "Powered by GallosOS" line under the logo — reuses the existing schema field, no new directive needed.

### 2. GRUB theme (initial increment: background and colors)

- **File** (destined for `build/assets/branding/grub/`): `background.png`, same `#1e1e2e` palette.
- **Pipeline change (Stage 5b, `build-iso.sh`):** Copy the background into `$STAGING/boot/grub/background.png` before final ISO assembly with `xorriso`, and extend the `grub.cfg` heredoc with:
  ```
  insmod gfxterm
  insmod png
  set gfxmode=auto
  terminal_output gfxterm
  background_image /boot/grub/background.png
  set menu_color_normal=white/black
  set menu_color_highlight=black/cyan
  ```
  (exact hex-equivalent GRUB color names to be picked at implementation time to match the navy/accent palette used elsewhere — GRUB's `menu_color_*` only accepts its fixed 16-color VGA-style palette by name, not arbitrary hex, which constrains how closely this can match the Plymouth/desktop palette).
- **Upgrade seam, not built now:** once `build-iso.sh` grows more than one `menuentry` (safe-mode, memtest86+, etc.), migrate to a full `theme.txt`-based GRUB theme (`+boot_menu` component, per-entry `classes` mapped to icon pixmaps) — the background/colors above become the fallback for terminals that can't render the fuller theme. This spec intentionally stops short of that today per the maintainer's explicit scope call.

### 3. Ubuntu de-branding inventory

Concrete, grounded in what the pipeline actually does today — not a generic "remove all Ubuntu branding" checklist:

| Where | Current state | Proposed treatment | Confidence |
| :--- | :--- | :--- | :--- |
| Plymouth boot splash | `plymouth-theme-ubuntu-text`, says "Ubuntu" | Replaced by the `gallos` theme above | Resolved by this design |
| GRUB boot menu | Already says "GallosOS Live" — no Ubuntu text | Nothing to do | Already correct |
| Desktop wallpaper | Already GallosOS flat-color PNGs (`02-provision.sh`) | Nothing to do | Already correct |
| Shell prompt (`\u@\h`) | Formerly `contestant@ubuntu` | Casper kernel cmdline `hostname=gallos` + daemon `hostnamectl set-hostname` on boot/reload. Systemd normalizes the static shell hostname to lowercase (for example, `contestant@icpc`); the pretty hostname retains organizer capitalization. | Implemented; Live guest verification pending |
| `/etc/os-release` `PRETTY_NAME` | `"Ubuntu 24.04.x LTS"` | Likely: change `PRETTY_NAME` to `"GallosOS ..."`, **keep** `ID_LIKE=ubuntu debian` (standard derivative-distro practice — e.g. Linux Mint does this — needed so `apt`/dependency resolution and any upstream `lsb_release`-sniffing tooling keeps working) | **⚠️ Open — verify against Canonical's actual trademark/branding policy before implementing.** Not asserted as legally settled here. |
| `/etc/lsb-release` | Mirrors `os-release` | Same treatment as above, same caveat | Same caveat |
| `/etc/issue` / `/etc/issue.net` (tty banner) | Stock Ubuntu getty banner | Low priority — the kiosk autologin (`/etc/profile.d/gallos-kiosk.sh`) launches `labwc` directly on tty1, so contestants never see this banner in normal operation; only relevant on a BIOS/rescue-mode tty fallback | Low priority, not blocking |
| APT vendor/sources branding | N/A | Contestants never see a GUI package manager in the kiosk session | Not applicable, no action |

### 4. Assets folder

```text
build/assets/branding/
├── README.md
├── plymouth/
│   └── README.md   # gallos.plymouth, gallos.script, logo-placeholder.png go here (Phase 4)
└── grub/
    └── README.md   # background.png goes here (Phase 4)
```

Created in this pass as scaffolding only (see each `README.md` for the per-folder contract). No image binaries are committed yet.

### 5. Config plumbing

No `schema/directives.schema.json` changes needed for the organizer-facing side — `[branding].boot_splash_logo_url`, `logo_url`, and `show_powered_by_gallos` already cover what's required, and `docs/CONFIG_SPEC.md` already documents the baked-in-only caveat correctly. The unresolved piece is entirely on the *build* side: `build.toml` has no field today telling a Track 2 custom build which `gallos.toml` to read `boot_splash_logo_url` from. Candidate shapes for that (e.g. a `branding_profile = "path/to/gallos.toml"` key under `[build]`, or defaulting silently to the bundled placeholder logo when absent) are left as an implementation-time decision, not resolved here.

## Open questions (resolve at Phase 4 kickoff, not now)

1. **Default logo/background provenance:** hand-authored artwork supplied by the maintainer, or programmatically generated placeholders (matching the existing flat-PNG pattern in `02-provision.sh`)? Both were presented as options during design and deliberately left open.
2. **`build.toml` → `gallos.toml` bridge:** exact mechanism for a Track 2 build to know which organizer branding to bake in.
3. **Ubuntu `os-release`/`lsb-release` rewrite:** needs a real check against Canonical's trademark/branding policy before any `PRETTY_NAME` change is implemented — this spec proposes a direction, not a cleared decision.
4. **GRUB `menu_color_*` exact values:** GRUB's built-in color names are a fixed small palette (not arbitrary hex) — pick the closest match to the navy/accent scheme at implementation time.

## References

- `ROADMAP.md` § Phase 4 — "Rapid White-Labeling and Branding Engine" bullet (this spec's parent item).
- `docs/CONFIG_SPEC.md` — `[branding]` schema and the "Architectural Caveat (Boot Splash)" note.
- `schema/directives.schema.json` — `branding` object definition.
- `docs/BUILD_SYSTEM.md` § 3, Stage 2 and Stage 5b — the two pipeline stages this design touches.
- `build/scripts/02-provision.sh`, `build/scripts/build-iso.sh`, `build/Containerfile` — inspected directly to ground every claim above in the actual current pipeline, not assumed Plymouth/GRUB conventions.
