# Local Root Recovery

GallosOS locks the root password in the built image and removes the `sudo` executables and configuration. An Organizer can enable local root recovery by placing a `crypt(3)` password hash in the **local** `gallos.toml`:

```toml
[recovery]
root_password_hash = "$6$rounds=656000$..."
```

The daemon requests `gallos-root-access.service` at boot and on reload. That service reads the hash only from a local configuration file and applies it with `chpasswd -e`; it has the `/etc` write access needed for password-file locking while the main daemon keeps its narrower filesystem sandbox. Keep the hash out of public profiles and use a strong unique password: a Contestant with physical access to the boot media may be able to copy the stored hash for offline guessing. Without a hash, root remains locked.

Scheduled Contest, Event, and Default transitions run under the root owned daemon and require no password entry. Read-only commands (`gallosctl status` and `gallosctl check`) can be run by any unprivileged user (including `contestant`). Mutating `gallosctl` commands (`contest start`, `contest stop`, `reload`) strictly require root access, enforced by the daemon via kernel peer credentials (`SO_PEERCRED`). With a hash configured, an Organizer can open a terminal in the normal kiosk and use `su root`. The configured root password remains available in every mode, including Contest, for physical recovery.

For a last-minute policy correction during Contest, the Organizer can edit `/etc/gallos/gallos.toml` with a local text editor and run `gallosctl reload`. This root-only directory takes precedence over policy on the approved boot medium. The daemon applies a valid file and reports success; malformed TOML reports an error and leaves the currently active policy in place. No boot arguments or network-fetched files can replace Organizer policy.

## Transition failure

The daemon stops the contestant session before changing firewall, storage, USB, browser, or workspace policy. It publishes the new mode and releases the kiosk only after required steps succeed. `gallosctl status` reports the committed `mode`, requested `target_mode`, `transition_status`, and `last_error`.

If a transition fails, the contestant kiosk stays stopped. When a local recovery hash is configured, GallosOS starts a root password prompt on tty1. The Organizer can inspect the error, repair the problem, and request a retry with `gallosctl contest start` or `gallosctl contest stop`. If root is locked, recovery requires repairing the image or local configuration offline and rebooting.

The root prompt is local to tty1. This feature does not install or enable SSH, open a network firewall port, or provide remote access. A complete Live-image QEMU test verified local root login, an active recovery console after transition failure, and manual retry. It has not been validated on physical contest hardware.
