# Local Root Recovery

GallosOS locks the root password in the built image and removes the `sudo` executables and configuration. An Organizer can enable local root recovery by placing a `crypt(3)` password hash in the **local** `gallos.toml`:

```toml
[recovery]
root_password_hash = "$6$rounds=656000$..."
```

The daemon requests `gallos-root-access.service` at boot and on reload. That service reads the hash only from a local configuration file and applies it with `chpasswd -e`; it has the `/etc` write access needed for password-file locking while the main daemon keeps its narrower filesystem sandbox. A remotely fetched configuration cannot set or replace the hash. Keep it out of public profiles and use a strong unique password: a Contestant with physical access to the boot media may be able to copy the stored hash for offline guessing. Without a hash, root remains locked.

Scheduled Contest, Event, and Default transitions run under the root owned daemon and require no password entry. Manual `gallos-ctl` commands require root access to the local control socket. With a hash configured, an Organizer can open a terminal in the normal kiosk and use `su root`. The configured root password remains available in every mode, including Contest, for physical recovery.

## Transition failure

The daemon stops the contestant session before changing firewall, storage, USB, browser, or workspace policy. It publishes the new mode and releases the kiosk only after required steps succeed. `gallos-ctl status` reports the committed `mode`, requested `target_mode`, `transition_status`, and `last_error`.

If a transition fails, the contestant kiosk stays stopped. When a local recovery hash is configured, GallosOS starts a root password prompt on tty1. The Organizer can inspect the error, repair the problem, and request a retry with `gallos-ctl contest start` or `gallos-ctl contest stop`. If root is locked, recovery requires repairing the image or local configuration offline and rebooting.

The root prompt is local to tty1. This feature does not install or enable SSH, open a network firewall port, or provide remote access. A complete Live-image QEMU test verified local root login, an active recovery console after transition failure, and manual retry. It has not been validated on physical contest hardware.
