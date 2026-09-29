"""Checks host-aware training egress configuration."""

import subprocess
from unittest.mock import patch

import pytest

from daemon.src.web_egress import build_squid_config, effective_websites, validate_website_list


def test_proxy_allows_exact_judges_and_no_general_tunnel():
    config = build_squid_config(["codeforces.com", "m1.codeforces.com"])
    assert "acl gallos_sites dstdomain codeforces.com m1.codeforces.com" in config
    assert "http_access allow gallos_local gallos_sites" in config
    assert "http_access deny all" in config
    assert "http_access deny CONNECT !SSL_ports" in config


@pytest.mark.parametrize(
    "site", ["*.codeforces.com", "https://codeforces.com", "127.0.0.1", "bad site"]
)
def test_proxy_rejects_ambiguous_or_non_domain_targets(site):
    with pytest.raises(ValueError):
        validate_website_list([site])


def test_event_inherits_default_sites_unless_explicitly_overridden():
    config = {"default": {"allowed_websites": ["codeforces.com"]}, "event": {}}
    assert effective_websites("Event", config) == ["codeforces.com"]
    config["event"]["allowed_websites"] = ["atcoder.jp"]
    assert effective_websites("Event", config) == ["atcoder.jp"]


def test_contest_stops_training_proxy():
    from daemon.src.web_egress import apply_web_egress

    with patch("subprocess.run") as run:
        apply_web_egress("Contest", {})
    run.assert_called_once_with(
        ["systemctl", "stop", "gallos-web-proxy.service"], check=True, timeout=20
    )


def test_open_club_mode_stops_training_proxy():
    from daemon.src.web_egress import apply_web_egress

    with patch("subprocess.run") as run:
        apply_web_egress("Default", {"default": {"allowed_websites": ["*"]}})
    run.assert_called_once_with(
        ["systemctl", "stop", "gallos-web-proxy.service"], check=True, timeout=20
    )


def test_failed_proxy_restart_restores_previous_policy(tmp_path):
    from daemon.src import web_egress

    policy = tmp_path / "squid.conf"
    policy.write_text("old policy\n")
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        if command[:2] == ["systemctl", "restart"] and len(calls) == 2:
            raise subprocess.CalledProcessError(1, command)

    with patch.object(web_egress, "PROXY_CONFIG", policy), patch("subprocess.run", side_effect=run):
        with pytest.raises(subprocess.CalledProcessError):
            web_egress.apply_web_egress(
                "Default", {"default": {"allowed_websites": ["codeforces.com"]}}
            )
    assert policy.read_text() == "old policy\n"
