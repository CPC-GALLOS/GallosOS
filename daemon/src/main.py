"""Main entry point for GallosOS Daemon (Python Core Engine).

Runs the primary daemon loop, handles Unix socket IPC commands from gallosctl,
and coordinates state machine ticks and dynamic policy enforcement.
"""

import contextlib
import json
import os
import queue
import select
import signal
import socket
import struct
import sys
import time
from pathlib import Path
from typing import Any

from .config import load_active_config, load_machine_config
from .firewall import FirewallManager
from .identity import apply_machine_identity
from .remote_policy import REMOTE_POLICY_URL_PATH, RemotePolicySync, read_source_url
from .root_access import apply_local_root_password
from .state_machine import ModeStateMachine

SOCKET_PATH = "/run/gallos/daemon.sock"
REMOTE_POLICY_CACHE_PATH = Path("/run/gallos/remote-policy.toml")


class GallosDaemon:
    """Main GallosOS Daemon coordinator."""

    def __init__(self) -> None:
        self.running = True
        self.config: dict[str, Any] = {}
        self.machine_cfg: dict[str, Any] = {}
        self.firewall = FirewallManager()
        self.state_machine: ModeStateMachine | None = None
        self.server_sock: socket.socket | None = None
        self.remote_policy_sync: RemotePolicySync | None = None
        self.pending_remote_configs: queue.SimpleQueue[dict[str, Any]] = queue.SimpleQueue()

    def setup_signals(self) -> None:
        """Configures OS signal handling."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGHUP, self._handle_sighup)

    def _handle_signal(self, signum, frame) -> None:
        print(f"[daemon] Received signal {signum}. Shutting down gracefully...")
        self.running = False

    def _handle_sighup(self, signum, frame) -> None:
        print("[daemon] Received SIGHUP. Reloading configuration...")
        self.reload_config()

    def reload_config(self, remote_config: dict[str, Any] | None = None) -> None:
        """Reloads active configuration on the fly."""
        if remote_config is None and self.remote_policy_sync:
            remote_config = self.remote_policy_sync.load_cached_policy()
        new_config = (
            load_active_config(remote_config) if remote_config is not None else load_active_config()
        )
        new_machine_cfg = load_machine_config()
        apply_machine_identity(new_config, new_machine_cfg)
        apply_local_root_password()
        self.config = new_config
        self.machine_cfg = new_machine_cfg
        if self.state_machine:
            self.state_machine.config = self.config
            self.state_machine.request_reapply()

    def _queue_remote_config(self, config: dict[str, Any]) -> None:
        self.pending_remote_configs.put(config)

    def _configure_remote_policy_sync(self) -> None:
        if not REMOTE_POLICY_URL_PATH.is_file():
            return
        try:
            source_url = read_source_url()
            self.remote_policy_sync = RemotePolicySync(
                source_url,
                REMOTE_POLICY_CACHE_PATH,
                self._queue_remote_config,
            )
        except (OSError, ValueError) as exc:
            print(f"[policy-sync] Remote policy sync disabled: {exc}", file=sys.stderr)

    def _apply_pending_remote_config(self) -> None:
        while True:
            try:
                remote_config = self.pending_remote_configs.get_nowait()
            except queue.Empty:
                return
            try:
                self.reload_config(remote_config)
            except Exception as exc:
                print(f"[policy-sync] Could not apply remote policy: {exc}", file=sys.stderr)

    def setup_socket(self) -> None:
        """Initializes the control Unix domain socket for gallosctl."""
        sock_dir = os.path.dirname(SOCKET_PATH)
        os.makedirs(sock_dir, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(sock_dir, 0o755)  # noqa: S103
        if os.path.exists(SOCKET_PATH):
            with contextlib.suppress(OSError):
                os.remove(SOCKET_PATH)

        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.bind(SOCKET_PATH)
        self.server_sock.listen(5)
        self.server_sock.setblocking(False)
        # Allow any local user to connect for status queries; mutating commands check UID
        os.chmod(SOCKET_PATH, 0o666)  # noqa: S103
        print(f"[daemon] IPC control socket listening at {SOCKET_PATH}")

    def _cmd_start(self, parts: list[str]) -> bytes:
        duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 300
        if self.state_machine:
            self.state_machine.set_manual_mode("Contest", duration_minutes=duration)
        return b"OK Contest transition requested\n"

    def _cmd_stop(self, _parts: list[str]) -> bytes:
        if self.state_machine:
            self.state_machine.set_manual_mode("Default")
        return b"OK Default transition requested\n"

    def _cmd_status(self, _parts: list[str]) -> bytes:
        cur_mode = self.state_machine.current_mode if self.state_machine else "Unknown"
        rem = 0
        if self.state_machine:
            _, rem = self.state_machine.evaluate_target_mode()
        status = {
            "mode": cur_mode,
            "remaining_seconds": rem,
            "target_mode": self.state_machine.target_mode if self.state_machine else "Unknown",
            "transition_status": (
                self.state_machine.transition_status if self.state_machine else "error"
            ),
            "last_error": (
                self.state_machine.last_error if self.state_machine else "Daemon initializing"
            ),
        }
        return (json.dumps(status) + "\n").encode("utf-8")

    def _cmd_reload(self, _parts: list[str]) -> bytes:
        try:
            self.reload_config()
        except Exception as exc:
            error = " ".join(str(exc).split()) or exc.__class__.__name__
            return f"ERROR Configuration reload failed: {error}\n".encode()
        return b"OK Configuration reloaded\n"

    def _process_ipc_command(self, raw_data: str, client_uid: int = 0) -> bytes:
        """Parses and dispatches IPC CLI commands, returning the response bytes."""
        parts = raw_data.split()
        if not parts:
            return b"ERROR Empty command\n"

        cmd = parts[0].upper()
        # Mutating operations strictly require root privileges (UID 0)
        if cmd in ("START", "STOP", "RELOAD") and client_uid != 0:
            return b"ERROR Permission denied: root required\n"

        handlers = {
            "START": self._cmd_start,
            "STOP": self._cmd_stop,
            "STATUS": self._cmd_status,
            "RELOAD": self._cmd_reload,
        }
        handler = handlers.get(cmd)
        if handler:
            return handler(parts)
        return b"ERROR Unknown command\n"

    def handle_socket_connection(self) -> None:
        """Accepts and handles incoming CLI IPC commands."""
        if not self.server_sock:
            return
        try:
            conn, _ = self.server_sock.accept()
            with conn:
                client_uid = 0
                if hasattr(socket, "SO_PEERCRED"):
                    try:
                        cred = conn.getsockopt(
                            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
                        )
                        _, client_uid, _ = struct.unpack("3i", cred)
                    except OSError:
                        client_uid = 0

                data = conn.recv(1024).decode("utf-8").strip()
                if not data:
                    return
                print(f"[daemon] IPC Command received from uid {client_uid}: '{data}'")
                response = self._process_ipc_command(data, client_uid=client_uid)
                conn.sendall(response)
        except Exception as e:
            print(f"[daemon] IPC handle error: {e}", file=sys.stderr)

    def run(self) -> None:
        """Main daemon service loop."""
        print("[daemon] Starting GallosOS Dynamic Daemon...")
        self.setup_signals()
        self.setup_socket()

        self._configure_remote_policy_sync()
        cached_policy = (
            self.remote_policy_sync.load_cached_policy() if self.remote_policy_sync else None
        )
        self.reload_config(cached_policy)

        # Start firewall manager
        self.firewall.start()
        self.state_machine = ModeStateMachine(self.config, self.firewall)
        if self.remote_policy_sync:
            self.remote_policy_sync.start()

        print("[daemon] Initialization complete. Entering state monitor loop.")
        while self.running:
            try:
                self._apply_pending_remote_config()
                # 1. State machine evaluation
                target_mode, rem_sec = self.state_machine.evaluate_target_mode()
                self.state_machine.transition_to(target_mode, rem_sec)

                # 2. Check for IPC client socket connections (timeout 1.0s)
                if self.server_sock:
                    rlist, _, _ = select.select([self.server_sock], [], [], 1.0)
                    if rlist:
                        self.handle_socket_connection()
                else:
                    time.sleep(1.0)

            except Exception as e:
                print(f"[daemon] Exception in main loop: {e}", file=sys.stderr)
                time.sleep(1.0)

        # Cleanup
        print("[daemon] Stopping firewall resolver thread and cleaning sockets...")
        if self.remote_policy_sync:
            self.remote_policy_sync.stop()
        self.firewall.stop()
        if self.server_sock:
            self.server_sock.close()
        if os.path.exists(SOCKET_PATH):
            with contextlib.suppress(OSError):
                os.remove(SOCKET_PATH)
        print("[daemon] GallosOS Daemon stopped.")


def main() -> None:
    daemon = GallosDaemon()
    daemon.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[daemon] Interrupted. Shutting down.", file=sys.stderr)
        sys.exit(130)
