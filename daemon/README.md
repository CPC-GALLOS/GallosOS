# GallosOS Daemon and Control Interface

## Overview

This directory contains the in-band Python daemon, the `gallosctl` command, and systemd units for mode transitions and host operations. The daemon applies Organizer policy to the Live workstation; optional network policy refresh and event storage do not require a Venue Controller to be present.

## Interface

- [Runtime modules](./src/README.md) implement `GallosDaemon`, `ModeStateMachine`, configuration loading, networking, storage, identity, and desktop integration. Provisioning in `/build/scripts/02-provision.sh` installs the package under `/usr/libexec/gallosd` and the controller as `/usr/bin/gallosctl`.
- [gallosctl](./gallosctl) exposes `status`, `check [--json]`, `reload`, `contest start [mins]`, and `contest stop` through `main()`. `send_command()` uses `/run/gallos/daemon.sock`; `run_check()` reads local status files and environment diagnostics.
- [gallosd.service](./gallosd.service) starts `python3 -m gallosd.main` from `/usr/libexec`, with explicit writable paths and capabilities.
- [gallos-event-storage.service](./gallos-event-storage.service), [gallos-usb-storage@.service](./gallos-usb-storage@.service), and [gallos-clean-state.service](./gallos-clean-state.service) invoke dedicated host helpers for optional event-data mounts, `lock`/`unlock` USB policy, and volatile scratch cleanup. Their `PrivateMounts=no` setting keeps those operations in the host mount namespace.
- [gallos-root-access.service](./gallos-root-access.service) invokes the local root-password helper; [gallos-recovery-console.service](./gallos-recovery-console.service) supplies the tty1 root login prompt. [gallos-web-proxy.service](./gallos-web-proxy.service) runs Squid as `proxy` using `/run/gallos/squid.conf`.

## Invariants

- `gallosctl.send_command()` requires root for control mutations; the daemon independently checks socket peer UID for `START`, `STOP`, and `RELOAD`. CLI checks alone are not the authorization boundary.
- Contest has precedence over Event in scheduled selection, with the configured mode as fallback. Explicit manual overrides are evaluated first: `contest stop` requests a continuing Default override. A positive `contest start` duration uses a monotonic timer and defaults to 300 minutes when omitted. See `ModeStateMachine.evaluate_target_mode()` in the runtime contract.
- Control replies acknowledge requests: `OK Contest transition requested` does not mean that transition application has completed. Inspect `status` fields including `target_mode`, `transition_status`, and `last_error`.
- `status` may fall back to cached state/transition JSON when the socket is absent or communication fails. `run_check()` also treats cached status as a running indication; these diagnostics alone do not prove current daemon liveness, network reachability, or graphical acceptance.
- Recovery credentials come from local directives. The separate host-service boundary allows required mount and password operations outside the main daemon's filesystem restrictions.

## Side Effects

- `gallosctl.send_command()` sends Unix-socket commands; `status` and `check` read local files and print diagnostics. Root control commands can trigger policy replacement, session termination, and destructive Contest cleanup through the runtime modules.
- The service units launch processes with their declared capabilities and filesystem access. Runtime operations change networking, USB authorization, mounts, managed browser policies, hostname, root-password state, and `/run/gallos` records; the [runtime contract](./src/README.md#side-effects) identifies those owners.

## Verification

Run `./scripts/check.sh` from the repository root. The focused unit command is `python3 -m pytest daemon/tests/ -v`; test directories are intentionally not contract packages.

Source and unit checks do not establish Live-image, graphical, or physical-hardware acceptance. Track those gates in `/ROADMAP.md` and follow `/docs/DEVELOPMENT.md` for the contributor environment.
