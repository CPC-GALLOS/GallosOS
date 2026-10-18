# GRUB Boot Menu Background

Not populated yet — see [`docs/BOOT_BRANDING.md`](../../../../docs/BOOT_BRANDING.md) § "2. GRUB theme" for the full design.

When implemented (Phase 4, initial branding increment), this folder will hold:

| File | Purpose |
| :--- | :--- |
| `background.png` | Full-screen background for the GRUB menu, same dark navy (`#1e1e2e`) palette as the Plymouth splash and desktop wallpaper. |

The planned Stage 5b integration will copy this into `$STAGING/boot/grub/background.png` before final `xorriso` assembly. The `grub.cfg` generation will gain `insmod gfxterm`, `insmod png`, `background_image /boot/grub/background.png`, and menu-color directives.

**Deferred beyond the initial branding increment:** a full `theme.txt` with per-entry icons. The current script already generates normal and `toram` entries; the agreed first branding scope remains a background and menu colors.
