"""Enterprise Managed Browser Policy module for GallosOS Daemon.

Generates managed JSON policies for Chromium and Firefox to restrict
browser navigation down to specific sub-URL paths during Contest mode.
"""

import json
import os
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .web_egress import effective_websites

CHROMIUM_POLICY_FILE = "/etc/chromium/policies/managed/gallos_policy.json"
FIREFOX_POLICY_FILE = "/etc/firefox/policies/policies.json"


def _build_allowed_urls(contest_cfg: dict[str, Any], browser_cfg: dict[str, Any]) -> list[str]:
    """Generates the list of allowed URL patterns."""
    allowed_urls: list[str] = list(browser_cfg.get("url_allowlist", []))
    if allowed_urls:
        return allowed_urls

    for site in contest_cfg.get("allowed_websites", []):
        clean_site = site.strip()
        if not clean_site:
            continue
        if "://" in clean_site:
            pattern = clean_site if clean_site.endswith("/*") else f"{clean_site}/*"
            allowed_urls.append(pattern)
        else:
            for scheme in ("https", "http"):
                allowed_urls.append(f"{scheme}://{clean_site}/*")
    return allowed_urls


def _chromium_exact_hosts(urls: list[str]) -> list[str]:
    """Prefix literal hosts so Chromium does not include their subdomains."""
    exact = []
    for pattern in urls:
        parts = urlsplit(pattern)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            exact.append(pattern)
            continue
        if parts.netloc.startswith(".") or "*" in parts.netloc or "@" in parts.netloc:
            exact.append(pattern)
            continue
        try:
            ip_address(parts.hostname)
        except ValueError:
            exact.append(
                urlunsplit(
                    (parts.scheme, f".{parts.netloc}", parts.path, parts.query, parts.fragment)
                )
            )
        else:
            exact.append(pattern)
    return exact


def _create_policy_payloads(
    mode: str, allowed_urls: list[str], blocked_urls: list[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Builds Chromium and Firefox policy payload dicts based on mode."""
    restricted = mode == "Contest" or bool(allowed_urls)
    if not restricted:
        return (
            {
                "URLBlocklist": [],
                "URLAllowlist": [],
                "MetricsReportingEnabled": False,
                "ProxyMode": "direct",
            },
            {
                "policies": {
                    "DisableTelemetry": True,
                    "DisableFirefoxStudies": True,
                    "Proxy": {"Mode": "none", "Locked": True},
                }
            },
        )

    chromium_payload = {
        "URLBlocklist": blocked_urls,
        "URLAllowlist": _chromium_exact_hosts(allowed_urls),
        "MetricsReportingEnabled": False,
        "PasswordManagerEnabled": False,
        "AutofillAddressEnabled": False,
        "AutofillCreditCardEnabled": False,
    }
    if mode == "Contest":
        chromium_payload["DefaultSearchProviderEnabled"] = False
        chromium_payload["ProxyMode"] = "direct"
    else:
        chromium_payload["ProxyMode"] = "fixed_servers"
        chromium_payload["ProxyServer"] = "http=127.0.0.1:3128;https=127.0.0.1:3128"
    firefox_payload = {
        "policies": {
            "WebsiteFilter": {
                "Block": ["<all_urls>" if item == "*" else item for item in blocked_urls],
                "Exceptions": allowed_urls,
            },
            "DisableFirefoxStudies": True,
            "DisableTelemetry": True,
            "PasswordManagerEnabled": False,
        }
    }
    if mode != "Contest":
        firefox_payload["policies"]["Proxy"] = {
            "Mode": "manual",
            "HTTPProxy": "127.0.0.1:3128",
            "SSLProxy": "127.0.0.1:3128",
            "Locked": True,
        }
    else:
        firefox_payload["policies"]["Proxy"] = {"Mode": "none", "Locked": True}
    return chromium_payload, firefox_payload


def _write_policy_json(file_path: str, payload: dict[str, Any]) -> None:
    """Safely writes a policy JSON payload to disk."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def apply_browser_policy(mode: str, config: dict[str, Any]) -> None:
    """Writes managed enterprise JSON policies for Chromium and Firefox."""
    mode_cfg = config.get(mode.lower(), {})
    browser_cfg = mode_cfg.get("browser_policy", {})
    sites = effective_websites(mode, config)
    mode_cfg = {**mode_cfg, "allowed_websites": sites}
    allowed_urls = _build_allowed_urls(mode_cfg, browser_cfg) if sites != ["*"] else []
    blocked_urls: list[str] = list(browser_cfg.get("url_blocklist", ["*"]))

    chromium_payload, firefox_payload = _create_policy_payloads(mode, allowed_urls, blocked_urls)

    _write_policy_json(CHROMIUM_POLICY_FILE, chromium_payload)
    _write_policy_json(FIREFOX_POLICY_FILE, firefox_payload)
    print(f"[browser_policy] Applied browser policies for mode '{mode}'")
