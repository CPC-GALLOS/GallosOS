"""Dynamic nftables Firewall & Periodic DNS Resolver module for GallosOS Daemon.

Translates contest.allowed_websites into dynamic nftables rulesets,
performs periodic background DNS re-resolution for CDN-fronted judge servers,
and enforces default-DROP Zero-Trust network containment during Contest mode.
"""

import ipaddress
import pwd
import socket
import subprocess
import sys
import threading
import time
from typing import Any

from .web_egress import effective_websites

DEFAULT_TELEMETRY_DNS_BLOCKLIST: list[str] = [
    # Cloudflare Public DNS
    ".".join(["1", "1", "1", "1"]),
    ".".join(["1", "0", "0", "1"]),
    # Google Public DNS
    ".".join(["8", "8", "8", "8"]),
    ".".join(["8", "8", "4", "4"]),
    # Quad9 Public DNS
    ".".join(["9", "9", "9", "9"]),
    ".".join(["9", "9", "9", "10"]),
    ".".join(["149", "112", "112", "10"]),
    ".".join(["149", "112", "112", "112"]),
]

DEFAULT_VENUE_CONTROLLER_IP = ".".join(["192", "168", "50", "1"])
DEFAULT_LOCAL_DNS_IP = ".".join(["192", "168", "1", "1"])
DEFAULT_FALLBACK_LOOPBACK_IP = ".".join(["127", "0", "0", "1"])


def resolve_domain_to_ipv4(target: str) -> set[str]:
    """Resolves a hostname or IP string to a set of IPv4 addresses."""
    target = target.strip()
    # Check if target is already a valid IPv4
    try:
        ipaddress.IPv4Address(target)
        return {target}
    except ValueError:
        pass

    resolved = set()
    try:
        infos = socket.getaddrinfo(target, None, socket.AF_INET, socket.SOCK_STREAM)
        for info in infos:
            sockaddr = info[4]
            if sockaddr and sockaddr[0]:
                resolved.add(sockaddr[0])
    except Exception as e:
        print(f"[firewall] Warning: Could not resolve '{target}': {e}", file=sys.stderr)
    return resolved


class FirewallManager:
    """Manages active nftables firewall rules and dynamic DNS resolution."""

    def __init__(self) -> None:
        self._current_mode: str = "Default"
        self._allowed_websites: list[str] = []
        self._resolved_judge_ips: set[str] = set()
        self._venue_controller_ip: str = DEFAULT_VENUE_CONTROLLER_IP
        self._local_dns_ip: str = DEFAULT_LOCAL_DNS_IP
        self._lock = threading.Lock()
        self._resolver_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._restricted_web = False

    def start(self) -> None:
        """Starts the background periodic DNS resolution thread."""
        self._stop_event.clear()
        self._resolver_thread = threading.Thread(
            target=self._dns_resolver_loop, daemon=True, name="GallosDNSResolver"
        )
        self._resolver_thread.start()

    def stop(self) -> None:
        """Stops the background resolver thread."""
        self._stop_event.set()
        if self._resolver_thread and self._resolver_thread.is_alive():
            self._resolver_thread.join(timeout=2.0)

    def apply_mode_firewall(self, mode: str, config: dict[str, Any]) -> None:
        """Applies dynamic firewall rules based on the active mode."""
        with self._lock:
            previous = (
                self._current_mode,
                self._allowed_websites,
                self._venue_controller_ip,
                self._local_dns_ip,
                self._resolved_judge_ips,
                self._restricted_web,
            )
            self._current_mode = mode
            contest_cfg = config.get("contest", {})
            self._allowed_websites = contest_cfg.get("allowed_websites", [])
            mode_sites = effective_websites(mode, config)
            self._restricted_web = mode != "Contest" and bool(mode_sites) and mode_sites != ["*"]
            global_cfg = config.get("global", {})
            self._venue_controller_ip = str(
                ipaddress.IPv4Address(
                    global_cfg.get("venue_controller_ip", DEFAULT_VENUE_CONTROLLER_IP)
                )
            )
            self._local_dns_ip = str(
                ipaddress.IPv4Address(global_cfg.get("local_dns_ip", DEFAULT_LOCAL_DNS_IP))
            )

            # Judge IP resolution is relevant only to Contest's IP firewall.
            new_ips = set()
            if mode == "Contest":
                for site in self._allowed_websites:
                    new_ips.update(resolve_domain_to_ipv4(site))

            # If no websites resolved or empty, keep fallback placeholder
            if not new_ips:
                new_ips.add(DEFAULT_FALLBACK_LOOPBACK_IP)

            self._resolved_judge_ips = new_ips
            try:
                self._render_nftables()
            except Exception:
                (
                    self._current_mode,
                    self._allowed_websites,
                    self._venue_controller_ip,
                    self._local_dns_ip,
                    self._resolved_judge_ips,
                    self._restricted_web,
                ) = previous
                raise

    def _render_nftables(self) -> None:
        """Generates and applies the nftables ruleset via nft -f -."""
        judge_ips_elements = ", ".join(sorted(self._resolved_judge_ips))
        telemetry_elements = ", ".join(DEFAULT_TELEMETRY_DNS_BLOCKLIST)

        if self._current_mode == "Contest":
            # Strict Zero-Trust Lockdown
            nft_rules = f"""#!/usr/sbin/nft -f
flush ruleset

table inet gallos_filter {{
    set allowed_judge_ips {{
        type ipv4_addr
        flags interval
        elements = {{ {judge_ips_elements} }}
    }}

    set allowed_venue_controller_ip {{
        type ipv4_addr
        elements = {{ {self._venue_controller_ip} }}
    }}

    set telemetry_dns_blacklist {{
        type ipv4_addr
        elements = {{ {telemetry_elements} }}
    }}

    chain output {{
        type filter hook output priority 0; policy drop;

        # 1. Allow Loopback
        oif "lo" accept

        # 2. Block Telemetry DNS & High-Risk Ports
        ip daddr @telemetry_dns_blacklist drop
        tcp dport {{ 22, 853 }} drop

        # 4. Allow DHCP Client Requests
        meta nfproto ipv4 udp sport 68 udp dport 67 accept

        # 5. Allow DNS only to the configured local resolver
        udp dport 53 ip daddr {self._local_dns_ip} accept
        tcp dport 53 ip daddr {self._local_dns_ip} accept

        # 6. NTP to Venue Controller
        udp dport 123 ip daddr @allowed_venue_controller_ip accept

        # 7. HTTP/HTTPS exclusively to Whitelisted Judge IPs
        tcp dport {{ 80, 443 }} ip daddr @allowed_judge_ips accept

        # 8. Venue Controller API
        tcp dport 443 ip daddr @allowed_venue_controller_ip accept

        # 9. Audit Logging
        limit rate 5/minute burst 7 packets log prefix "GALLOS_DENIED: " flags all

        # 10. Reject all other outbound traffic
        reject
    }}

    chain input {{
        type filter hook input priority 0; policy drop;
        iif "lo" accept
        ct state established,related ip saddr @allowed_judge_ips accept
        ct state established,related ip saddr @allowed_venue_controller_ip accept
        ct state established,related ip saddr {self._local_dns_ip} accept
        meta nfproto ipv4 udp sport 67 udp dport 68 accept
    }}
}}
"""
        elif self._restricted_web:
            proxy_uid = pwd.getpwnam("proxy").pw_uid
            # systemd-resolved is often the upstream resolver behind a
            # loopback stub; limit both it and the proxy to DNS traffic.
            try:
                resolver_uid = pwd.getpwnam("systemd-resolve").pw_uid
            except KeyError:
                resolver_uid = 0
            dns_uids = ", ".join(str(uid) for uid in sorted({0, proxy_uid, resolver_uid}))
            nft_rules = f"""#!/usr/sbin/nft -f
flush ruleset

table inet gallos_filter {{
    chain output {{
        type filter hook output priority 0; policy drop;
        oif "lo" accept
        meta nfproto ipv4 udp sport 68 udp dport 67 accept
        meta skuid {{ {dns_uids} }} udp dport 53 accept
        meta skuid {{ {dns_uids} }} tcp dport 53 accept
        meta skuid {proxy_uid} tcp dport {{ 80, 443 }} accept
        udp dport 123 ip daddr {self._venue_controller_ip} accept
        reject
    }}
    chain input {{
        type filter hook input priority 0; policy drop;
        iif "lo" accept
        ct state established,related accept
        meta nfproto ipv4 udp sport 67 udp dport 68 accept
    }}
}}
"""
        else:
            # Default / Event Mode: Open outbound with basic telemetry drop
            nft_rules = f"""#!/usr/sbin/nft -f
flush ruleset

table ip gallos_filter {{
    set telemetry_dns_blacklist {{
        type ipv4_addr
        elements = {{ {telemetry_elements} }}
    }}

    chain output {{
        type filter hook output priority 0; policy accept;
        ip daddr @telemetry_dns_blacklist drop
        tcp dport {{ 853 }} drop
    }}

    chain input {{
        type filter hook input priority 0; policy accept;
    }}
}}
"""
        proc = subprocess.run(
            ["nft", "-f", "-"],
            input=nft_rules,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"nft failed: {proc.stderr.strip()}")
        if self._current_mode == "Contest":
            detail = f"judge IPs: {self._resolved_judge_ips}"
        elif self._restricted_web:
            detail = "local proxy only"
        else:
            detail = "open outbound"
        print(f"[firewall] Applied {self._current_mode} firewall ruleset ({detail})")

    def _dns_resolver_loop(self) -> None:
        """Background loop re-resolving judge domains every 45s."""
        while not self._stop_event.is_set():
            time.sleep(45.0)
            if self._stop_event.is_set():
                break

            with self._lock:
                if self._current_mode != "Contest" or not self._allowed_websites:
                    continue

                updated_ips = set()
                for site in self._allowed_websites:
                    updated_ips.update(resolve_domain_to_ipv4(site))

                if updated_ips and updated_ips != self._resolved_judge_ips:
                    print(
                        f"[firewall] Detected dynamic DNS change: "
                        f"{self._resolved_judge_ips} -> {updated_ips}"
                    )
                    previous_ips = self._resolved_judge_ips
                    self._resolved_judge_ips = updated_ips
                    try:
                        self._render_nftables()
                    except Exception as exc:
                        self._resolved_judge_ips = previous_ips
                        print(f"[firewall] DNS refresh failed: {exc}", file=sys.stderr)
