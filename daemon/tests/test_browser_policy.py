"""Unit tests for gallosd enterprise browser policy module."""

from daemon.src.browser_policy import _build_allowed_urls, _create_policy_payloads


def test_build_allowed_urls_from_allowed_websites():
    contest_cfg = {"allowed_websites": ["boca.local", "https://judge.icpc.global"]}
    browser_cfg = {}
    urls = _build_allowed_urls(contest_cfg, browser_cfg)
    assert "https://boca.local/*" in urls
    assert "http://boca.local/*" in urls
    assert "https://judge.icpc.global/*" in urls


def test_create_policy_payloads_contest_mode():
    allowed = ["https://boca.local/*"]
    blocked = ["*"]
    ch_payload, ff_payload = _create_policy_payloads("Contest", allowed, blocked)
    assert ch_payload["URLBlocklist"] == ["*"]
    assert ch_payload["URLAllowlist"] == ["https://.boca.local/*"]
    assert ch_payload["DefaultSearchProviderEnabled"] is False
    assert ch_payload["ProxyMode"] == "direct"
    assert ff_payload["policies"]["WebsiteFilter"]["Block"] == ["<all_urls>"]
    assert ff_payload["policies"]["WebsiteFilter"]["Exceptions"] == allowed
    assert ff_payload["policies"]["DisableTelemetry"] is True


def test_create_policy_payloads_default_mode():
    ch_payload, ff_payload = _create_policy_payloads("Default", [], ["*"])
    assert ch_payload["URLBlocklist"] == []
    assert ch_payload["URLAllowlist"] == []
    assert ch_payload["ProxyMode"] == "direct"
    assert ff_payload["policies"]["DisableTelemetry"] is True
    assert ff_payload["policies"]["Proxy"] == {"Mode": "none", "Locked": True}


def test_default_mode_with_named_sites_restricts_browser():
    allowed = ["https://codeforces.com/*", "https://m1.codeforces.com/*"]
    ch_payload, ff_payload = _create_policy_payloads("Default", allowed, ["*"])
    assert ch_payload["URLBlocklist"] == ["*"]
    assert ch_payload["URLAllowlist"] == [
        "https://.codeforces.com/*",
        "https://.m1.codeforces.com/*",
    ]
    assert ff_payload["policies"]["WebsiteFilter"]["Block"] == ["<all_urls>"]
    assert ff_payload["policies"]["WebsiteFilter"]["Exceptions"] == allowed
