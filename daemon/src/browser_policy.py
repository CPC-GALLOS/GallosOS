"""Enterprise Managed Browser Policy module for GallosOS Daemon.

Generates managed JSON policies for Chromium and Firefox to restrict
browser navigation down to specific sub-URL paths during Contest mode.
"""

import json
import os
from typing import Any

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


def _create_policy_payloads(
    mode: str, allowed_urls: list[str], blocked_urls: list[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Builds Chromium and Firefox policy payload dicts based on mode."""
    if mode != "Contest":
        return {"URLBlocklist": [], "URLAllowlist": []}, {"policies": {}}

    chromium_payload = {
        "URLBlocklist": blocked_urls,
        "URLAllowlist": allowed_urls,
        "DefaultSearchProviderEnabled": False,
        "PasswordManagerEnabled": False,
        "AutofillAddressEnabled": False,
        "AutofillCreditCardEnabled": False,
    }
    firefox_payload = {
        "policies": {
            "WebsiteFilter": {
                "Block": blocked_urls,
                "Exceptions": allowed_urls,
            },
            "DisableFirefoxStudies": True,
            "DisableTelemetry": True,
            "PasswordManagerEnabled": False,
        }
    }
    return chromium_payload, firefox_payload


def _write_policy_json(file_path: str, payload: dict[str, Any]) -> None:
    """Safely writes a policy JSON payload to disk."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def apply_browser_policy(mode: str, config: dict[str, Any]) -> None:
    """Writes managed enterprise JSON policies for Chromium and Firefox."""
    contest_cfg = config.get("contest", {})
    browser_cfg = contest_cfg.get("browser_policy", {})
    allowed_urls = _build_allowed_urls(contest_cfg, browser_cfg)
    blocked_urls: list[str] = list(browser_cfg.get("url_blocklist", ["*"]))

    chromium_payload, firefox_payload = _create_policy_payloads(mode, allowed_urls, blocked_urls)

    _write_policy_json(CHROMIUM_POLICY_FILE, chromium_payload)
    _write_policy_json(FIREFOX_POLICY_FILE, firefox_payload)
    print(f"[browser_policy] Applied browser policies for mode '{mode}'")
