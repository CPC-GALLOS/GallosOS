"""Unit tests for gallos-daemon dynamic firewall module."""

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
        assert "udp sport 68 udp dport 67 accept" in rules
        assert "udp sport 67 udp dport 68 accept" in rules
