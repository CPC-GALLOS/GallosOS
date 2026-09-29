"""Unit tests for gallosd dynamic firewall module."""

from unittest.mock import MagicMock, patch

from daemon.src.firewall import FirewallManager, resolve_domain_to_ipv4


def test_resolve_domain_to_ipv4_direct_ip():
    res = resolve_domain_to_ipv4("192.168.1.100")
    assert res == {"192.168.1.100"}


def test_resolve_domain_to_ipv4_hostname():
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("10.0.0.5", 80))]):
        res = resolve_domain_to_ipv4("boca.contest.org")
        assert "10.0.0.5" in res


def test_firewall_apply_default_mode():
    mgr = FirewallManager()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        mgr.apply_mode_firewall("Default", {})
        assert mock_run.called
        call_kwargs = mock_run.call_args[1]
        assert "nft" in mock_run.call_args[0][0]
        rules = call_kwargs["input"]
        assert "policy accept" in rules


def test_firewall_apply_contest_mode():
    mgr = FirewallManager()
    config = {
        "contest": {"allowed_websites": ["192.168.50.10"]},
        "global": {"venue_controller_ip": "192.168.50.1", "local_dns_ip": "192.168.1.1"},
    }
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        mgr.apply_mode_firewall("Contest", config)
        assert mock_run.called
        rules = mock_run.call_args[1]["input"]
        assert "policy drop" in rules
        assert "192.168.50.10" in rules
        assert "192.168.50.1" in rules
        assert "GALLOS_DENIED: " in rules
        assert "meta nfproto ipv4 udp sport 68 udp dport 67 accept" in rules
        assert "meta nfproto ipv4 udp sport 67 udp dport 68 accept" in rules


def test_contest_dns_is_limited_to_the_configured_resolver():
    mgr = FirewallManager()
    config = {
        "global": {"local_dns_ip": "192.168.1.1"},
    }
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        mgr.apply_mode_firewall("Contest", config)

    rules = mock_run.call_args.kwargs["input"]
    assert "udp dport 53 ip daddr 192.168.1.1 accept" in rules
    assert "tcp dport 53 ip daddr 192.168.1.1 accept" in rules
    assert "udp dport 53 accept" not in rules
    assert "tcp dport 53 accept" not in rules


def test_contest_output_rechecks_existing_flows_against_allowlists():
    mgr = FirewallManager()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        mgr.apply_mode_firewall("Contest", {})

    rules = mock_run.call_args.kwargs["input"]
    output_chain = rules.split("chain output {", maxsplit=1)[1].split("chain input {", maxsplit=1)[
        0
    ]
    assert "ct state established,related accept" not in output_chain


def test_training_default_limits_egress_to_proxy_identity():
    mgr = FirewallManager()
    config = {"default": {"allowed_websites": ["codeforces.com"]}}
    with (
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
        patch("pwd.getpwnam", return_value=MagicMock(pw_uid=13)),
    ):
        mgr.apply_mode_firewall("Default", config)
    rules = mock_run.call_args.kwargs["input"]
    assert "table inet gallos_filter" in rules
    assert "policy drop" in rules
    assert "meta nfproto ipv4 udp sport 68 udp dport 67 accept" in rules
    assert "meta skuid" in rules
    assert "tcp dport { 80, 443 }" in rules
    assert (
        "ct state established,related accept"
        not in rules.split("chain output {", 1)[1].split("chain input {", 1)[0]
    )


def test_contest_filters_ipv6_as_well_as_ipv4():
    mgr = FirewallManager()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        mgr.apply_mode_firewall("Contest", {})

    rules = mock_run.call_args.kwargs["input"]
    assert "table inet gallos_filter" in rules
    assert "policy drop" in rules


def test_training_event_uses_event_allowlist():
    mgr = FirewallManager()
    config = {
        "default": {"allowed_websites": ["*"]},
        "event": {"allowed_websites": ["atcoder.jp"]},
    }
    with (
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
        patch("pwd.getpwnam", return_value=MagicMock(pw_uid=13)),
    ):
        mgr.apply_mode_firewall("Event", config)
    assert "policy drop" in mock_run.call_args.kwargs["input"]


def test_training_event_without_override_inherits_default_allowlist():
    mgr = FirewallManager()
    config = {"default": {"allowed_websites": ["codeforces.com"]}, "event": {}}
    with (
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
        patch("pwd.getpwnam", return_value=MagicMock(pw_uid=13)),
    ):
        mgr.apply_mode_firewall("Event", config)
    assert "policy drop" in mock_run.call_args.kwargs["input"]
