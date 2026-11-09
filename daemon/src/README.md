# GallosOS Runtime Modules

## Overview

These Python modules implement the Live system daemon and its host-service helpers. The image provisions them as the `gallosd` package under `/usr/libexec`; the service entry point is `python3 -m gallosd.main`. Module operations affect the running workstation. See the [service and CLI contract](../README.md) for the installed boundary.

## Interface

| Module | Public entry points and responsibility |
| :--- | :--- |
| [main.py](./main.py) | `GallosDaemon.run()`, `reload_config()`, and `main()` coordinate policy, the mode loop, signals, and Unix-socket commands. |
| [config.py](./config.py) | `load_local_config()`, `load_machine_config()`, `load_active_config()`, `validate_directives()`, and `is_config_expired()` discover TOML inputs and validate organizer directives. |
| [state_machine.py](./state_machine.py) | `ModeStateMachine.evaluate_target_mode()`, `set_manual_mode()`, `request_reapply()`, and `transition_to()` select and apply modes; `perform_clean_state_wipe()` resets the contestant home. |
| [remote_policy.py](./remote_policy.py) | `read_source_url()`, `fetch_remote_policy()`, and `RemotePolicySync` provide optional HTTPS refresh, callbacks, and a live-session cache. |
| [firewall.py](./firewall.py) | `FirewallManager.start()`, `stop()`, and `apply_mode_firewall()` manage nftables and periodic Contest DNS resolution; `resolve_domain_to_ipv4()` resolves individual targets. |
| [web_egress.py](./web_egress.py), [browser_policy.py](./browser_policy.py) | `effective_websites()`, `validate_website_list()`, `build_squid_config()`, and `apply_web_egress()` manage proxy policy; `apply_browser_policy()` writes Chromium and Firefox managed policies. |
| [storage.py](./storage.py), [event_storage_host.py](./event_storage_host.py) | Both expose `mount_event_data()` and `unmount_event_data()`; the first delegates through systemd, and the second performs host mount operations. |
| [usb_manager.py](./usb_manager.py), [usb_storage_host.py](./usb_storage_host.py) | `set_usb_storage_allowed()` delegates to the host service; `apply_usb_policy()` changes mount and USB-interface authorization policy. |
| [clean_state.py](./clean_state.py), [clean_state_host.py](./clean_state_host.py) | `reset_contest_scratch()` delegates cleanup; host `main()`, `mount_inventory()`, `cleanup_roots()`, `detach_data_mounts()`, `cleanup_owned_files()`, and `overlay_backing_paths()` inspect and clear contestant-owned volatile storage. |
| [session_gate.py](./session_gate.py), [transition_record.py](./transition_record.py) | `stop_kiosk()`, `start_recovery_console()`, and `release_kiosk()` gate tty1; `write_record()` and `read_record()` preserve transition state across daemon restarts. |
| [identity.py](./identity.py), [desktop.py](./desktop.py) | `get_local_mac_addresses()` and `apply_machine_identity()` resolve workstation identity; `update_wallpaper()`, `send_desktop_notification()`, and `export_waybar_state()` update desktop outputs. |
| [root_access.py](./root_access.py), [root_access_host.py](./root_access_host.py) | `apply_local_root_password()` starts the dedicated host service; host `main()` supplies the local hash to `set_root_password()`. |

## Invariants

- `config.load_local_config()` prefers canonical `gallos.toml` files in search-directory order, then one unambiguous named profile, then the bundled baseline. `load_active_config()` validates selected directives against the JSON Schema and permits remote replacement only when the selected source is the bundled baseline. Recovery credentials are re-read from local configuration.
- `ModeStateMachine.evaluate_target_mode()` evaluates a manual override first, then Contest triggers, Event schedules, and the configured fallback mode (normally Default). Schedule windows include their start and exclude their end. `set_manual_mode("Default")` remains an override until cleared or the system reboots; it does not resume scheduled selection immediately.
- `transition_to()` stops the kiosk for mode changes and startup recovery; same-mode hot reload retains running applications and stops them only on a required failure. Transition errors latch; `set_manual_mode()` explicitly clears the error for another attempt, while reload's `request_reapply()` alone does not. Recording an error does not roll back host actions already performed. Reapplying an existing Contest policy does not repeat the contestant-home wipe. `transition_record.read_record()` converts an interrupted pending transition into an error.
- `GallosDaemon.handle_socket_connection()` obtains peer credentials, and command dispatch requires UID 0 for `START`, `STOP`, and `RELOAD`; `STATUS` is available to other local users. Remote refresh callbacks queue work for the daemon loop.
- `fetch_remote_policy()` requires HTTPS without embedded credentials, validates the final response origin, caps the response at 1 MiB, and validates UTF-8 TOML against the schema. `RemotePolicySync` retains a cache under `/run`; this is not persistent offline storage.
- `effective_websites()` lets Event inherit Default's website list unless overridden. Restricted proxy lists accept literal DNS names or IPv4 addresses. `FirewallManager` renders different Contest, restricted-practice, and open-mode rules; open mode still contains explicit public-DNS destination and TCP 853 drops.
- `event_storage_host.mount_event_data()` tolerates an absent optional partition, but rejects duplicate labels, non-ext4 media, and a mismatched mounted source. `clean_state_host.cleanup_roots()` requires a writable volatile Live root; cleanup excludes the separately handled home, nested mounts, and overlay backing paths. USB locking preserves interfaces identified as backing protected system mounts.

## Side Effects

- `FirewallManager` resolves DNS, runs a background thread, and submits rules beginning with `flush ruleset` through `nft -f -`. Proxy application runs Squid validation and systemd actions; browser policy replaces managed JSON files under `/etc/chromium` and `/etc/firefox`.
- Mode changes stop tty1 and kill contestant processes. Contest entry unmounts event storage, invokes scratch cleanup, deletes `/home/contestant` contents, restores `/etc/skel`, and changes ownership. Host helpers mount/unmount filesystems, change USB sysfs authorization, and write/remove udev and polkit rules.
- Configuration reload changes the hostname and root-password state through host commands/services. Identity, Waybar state, the kiosk-ready marker, transition records, the control socket, proxy configuration, and remote cache occupy `/run/gallos`. Optional remote refresh performs HTTPS requests; transition records and remote caches use temporary files followed by replacement.
- Desktop helpers invoke `swaybg` and `notify-send` through the contestant account. Several desktop/output errors are logged rather than raised, so a successful policy transition alone does not establish successful graphical presentation.

## Verification

From the repository root, run `./scripts/check.sh`. For focused daemon unit checks, run `python3 -m pytest daemon/tests/ -v`.

These checks cover source and unit behavior. Booted-image policy enforcement, graphical session behavior, and physical hardware acceptance require separate evidence; see `/ROADMAP.md` and `/docs/DEVELOPMENT.md`.

### Updated runtime contracts

`ModeStateMachine.replace_config()` retains active Contest deadlines and applies
explicit end changes. The transition journal stores absolute ends and monotonic
origins for daemon restarts within the same boot. Expiration suppresses automatic
starts without interrupting an active Contest. `gallosctl contest stop` remains
an explicit Default override; natural manual expiry resumes schedule selection.
