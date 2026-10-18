# Branding Assets (`build/assets/branding/`)

This directory is reserved for planned build-time Plymouth and GRUB branding assets. Once implemented, the pipeline will bake them into the ISO; runtime policy refresh will not regenerate boot assets.

**Status: scaffolding only.** This folder is a placeholder for ROADMAP Phase 4 ("Contestant Workstation Features"). No build script currently reads from it. The asset contract and open decisions are described in [`docs/BOOT_BRANDING.md`](../../../docs/BOOT_BRANDING.md).

## Layout

```text
build/assets/branding/
├── plymouth/   # Plymouth "script" theme source (gallos.plymouth, gallos.script, default logo)
└── grub/       # GRUB boot menu background image and (later) a full theme.txt
```

See each subfolder's `README.md` for format/resolution expectations and which pipeline stage consumes it.
