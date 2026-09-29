"""Tests for build-trusted remote policy refresh."""

from pathlib import Path
from unittest.mock import patch

import pytest

from daemon.src.remote_policy import RemotePolicySync, fetch_remote_policy, read_source_url

VALID_TOML = b'[global]\ntimezone = "UTC"\n'


class FakeResponse:
    def __init__(self, body: bytes, url: str = "https://policy.example/gallos.toml"):
        self.body = body
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]

    def geturl(self) -> str:
        return self.url


def test_read_source_url_requires_https(tmp_path: Path) -> None:
    source = tmp_path / "url.txt"
    source.write_text("http://policy.example/gallos.toml\n", encoding="utf-8")

    with pytest.raises(ValueError, match="HTTPS"):
        read_source_url(source)


def test_fetch_rejects_redirect_out_of_https(tmp_path: Path) -> None:
    source = tmp_path / "url.txt"
    source.write_text("https://policy.example/gallos.toml\n", encoding="utf-8")

    with patch(
        "daemon.src.remote_policy.urlopen",
        return_value=FakeResponse(VALID_TOML, "http://policy.example/gallos.toml"),
    ):
        with pytest.raises(ValueError, match="HTTPS"):
            fetch_remote_policy(read_source_url(source))


def test_refresh_validates_then_atomically_caches_and_applies(tmp_path: Path) -> None:
    cache = tmp_path / "remote-policy.toml"
    applied = []
    sync = RemotePolicySync(
        "https://policy.example/gallos.toml",
        cache,
        applied.append,
        fetcher=lambda _url: VALID_TOML,
    )

    assert sync.refresh_once() is True
    assert cache.read_bytes() == VALID_TOML
    assert applied == [{"global": {"timezone": "UTC"}}]
    assert list(tmp_path.glob("*.tmp")) == []


def test_invalid_remote_policy_does_not_replace_cache_or_active_policy(tmp_path: Path) -> None:
    cache = tmp_path / "remote-policy.toml"
    cache.write_bytes(VALID_TOML)
    applied = []
    sync = RemotePolicySync(
        "https://policy.example/gallos.toml",
        cache,
        applied.append,
        fetcher=lambda _url: b"[global]\nunknown = 1\n",
    )

    assert sync.refresh_once() is False
    assert cache.read_bytes() == VALID_TOML
    assert applied == []


def test_offline_fetch_leaves_policy_unchanged(tmp_path: Path) -> None:
    cache = tmp_path / "remote-policy.toml"
    applied = []

    def fail(_url: str) -> bytes:
        raise OSError("offline")

    sync = RemotePolicySync(
        "https://policy.example/gallos.toml", cache, applied.append, fetcher=fail
    )

    assert sync.refresh_once() is False
    assert not cache.exists()
    assert applied == []


def test_unchanged_policy_does_not_request_runtime_reapply(tmp_path: Path) -> None:
    cache = tmp_path / "remote-policy.toml"
    cache.write_bytes(VALID_TOML)
    applied = []
    sync = RemotePolicySync(
        "https://policy.example/gallos.toml",
        cache,
        applied.append,
        fetcher=lambda _url: VALID_TOML,
    )

    assert sync.refresh_once() is True
    assert applied == []
