"""Main entry point for GallosOS Daemon (Python Core Engine).

Runs the primary daemon loop, handles Unix socket IPC commands from gallos-ctl,
and coordinates state machine ticks and dynamic policy enforcement.
"""

import contextlib
import json
import os
import select
import signal
import socket
import sys
import time
from typing import Any

from .config import load_active_config, load_machine_config
from .firewall import FirewallManager
from .identity import apply_machine_identity
from .root_access import apply_local_root_password
from .state_machine import ModeStateMachine

SOCKET_PATH = "/run/gallos/daemon.sock"


class GallosDaemon:
    """Main GallosOS Daemon coordinator."""

    def __init__(self) -> None:
        self.running = True
        self.config: dict[str, Any] = {}
        self.machine_cfg: dict[str, Any] = {}
        self.firewall = FirewallManager()
        self.state_machine: ModeStateMachine | None = None
        self.server_sock: socket.socket | None = None

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

    def reload_config(self) -> None:
        """Reloads active configuration on the fly."""
        self.config = load_active_config()
        self.machine_cfg = load_machine_config()
        apply_machine_identity(self.config, self.machine_cfg)
        apply_local_root_password()
        if self.state_machine:
            self.state_machine.config = self.config
            self.state_machine.request_reapply()

    def setup_socket(self) -> None:
        """Initializes the control Unix domain socket for gallos-ctl."""
        os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
        if os.path.exists(SOCKET_PATH):
            with contextlib.suppress(OSError):
                os.remove(SOCKET_PATH)

        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.bind(SOCKET_PATH)
        self.server_sock.listen(5)
        self.server_sock.setblocking(False)
        # Root and wheel access
        os.chmod(SOCKET_PATH, 0o660)
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
        self.reload_config()
        return b"OK Configuration reloaded\n"

    def _process_ipc_command(self, raw_data: str) -> bytes:
        """Parses and dispatches IPC CLI commands, returning the response bytes."""
        parts = raw_data.split()
        if not parts:
            return b"ERROR Empty command\n"

        handlers = {
            "START": self._cmd_start,
            "STOP": self._cmd_stop,
            "STATUS": self._cmd_status,
            "RELOAD": self._cmd_reload,
        }
        cmd = parts[0].upper()
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
                data = conn.recv(1024).decode("utf-8").strip()
                if not data:
                    return
                print(f"[daemon] IPC Command received: '{data}'")
                response = self._process_ipc_command(data)
                conn.sendall(response)
        except Exception as e:
            print(f"[daemon] IPC handle error: {e}", file=sys.stderr)

    def run(self) -> None:
        """Main daemon service loop."""
        print("[daemon] Starting GallosOS Dynamic Daemon...")
        self.setup_signals()
        self.setup_socket()

        # Ingest configs
        self.reload_config()

        # Start firewall manager
        self.firewall.start()
        self.state_machine = ModeStateMachine(self.config, self.firewall)

        print("[daemon] Initialization complete. Entering state monitor loop.")
        while self.running:
            try:
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
    main()
