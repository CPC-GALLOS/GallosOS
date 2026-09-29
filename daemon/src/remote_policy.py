"""HTTPS refresh for policy sources explicitly embedded in a custom ISO."""

import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

import tomllib

from .config import validate_directives

MAX_POLICY_BYTES = 1024 * 1024
FETCH_TIMEOUT_SECONDS = 8
DEFAULT_REFRESH_INTERVAL_SECONDS = 300
REMOTE_POLICY_URL_PATH = Path("/cdrom/gallos/config/remote-policy-url.txt")


def _require_https_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Remote policy source must be an HTTPS URL without embedded credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Remote policy source has an invalid port") from exc
    if port == 0:
        raise ValueError("Remote policy source has an invalid port")
    return url


def _origin(url: str) -> tuple[str, int]:
    parsed = urlsplit(url)
    return parsed.hostname.lower(), parsed.port or 443


def read_source_url(path: Path = REMOTE_POLICY_URL_PATH) -> str:
    """Read and validate the immutable, build-injected URL file."""
    url = path.read_text(encoding="utf-8").strip()
    if not url:
        raise ValueError("Remote policy source URL is empty")
    return _require_https_url(url)


def _parse_policy(payload: bytes) -> dict[str, Any]:
    try:
        config = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Remote policy is not valid UTF-8 TOML: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("Remote policy root must be a TOML table")
    validate_directives(config)
    return config


def fetch_remote_policy(url: str) -> bytes:
    """Fetch a bounded TOML response over validated HTTPS."""
    trusted_url = _require_https_url(url)
    with urlopen(trusted_url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        final_url = _require_https_url(response.geturl())
        if _origin(final_url) != _origin(trusted_url):
            raise ValueError("Remote policy redirect changed the trusted host")
        payload = response.read(MAX_POLICY_BYTES + 1)
    if len(payload) > MAX_POLICY_BYTES:
        raise ValueError(f"Remote policy exceeds {MAX_POLICY_BYTES} bytes")
    _parse_policy(payload)
    return payload


class RemotePolicySync:
    """Periodically fetch, validate, cache, and publish remote policy updates."""

    def __init__(
        self,
        url: str,
        cache_path: Path,
        on_update: Callable[[dict[str, Any]], None],
        fetcher: Callable[[str], bytes] = fetch_remote_policy,
        interval_seconds: int = DEFAULT_REFRESH_INTERVAL_SECONDS,
    ) -> None:
        self.url = _require_https_url(url)
        self.cache_path = cache_path
        self.on_update = on_update
        self.fetcher = fetcher
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def load_cached_policy(self) -> dict[str, Any] | None:
        """Return only a valid last-known-good policy from this live boot."""
        try:
            payload = self.cache_path.read_bytes()
            if len(payload) > MAX_POLICY_BYTES:
                raise ValueError("Cached policy exceeds size limit")
            return _parse_policy(payload)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            print(f"[policy-sync] Ignoring invalid cached policy: {exc}")
            return None

    def _write_cache(self, payload: bytes) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=".remote-policy-", suffix=".tmp", dir=self.cache_path.parent
        )
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as cache_file:
                cache_file.write(payload)
                cache_file.flush()
                os.fsync(cache_file.fileno())
            os.replace(temporary_name, self.cache_path)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            Path(temporary_name).unlink(missing_ok=True)
            raise

    def refresh_once(self) -> bool:
        """Apply a valid update; fetch, parse, and schema failures leave policy unchanged."""
        try:
            payload = self.fetcher(self.url)
            if len(payload) > MAX_POLICY_BYTES:
                raise ValueError(f"Remote policy exceeds {MAX_POLICY_BYTES} bytes")
            config = _parse_policy(payload)
            try:
                if self.cache_path.read_bytes() == payload:
                    return True
            except FileNotFoundError:
                pass
            self.on_update(config)
            try:
                self._write_cache(payload)
            except OSError as exc:
                print(f"[policy-sync] Could not retain live-session cache: {exc}")
            print("[policy-sync] Applied validated remote policy update")
            return True
        except Exception as exc:
            print(f"[policy-sync] Remote policy refresh failed; keeping active policy: {exc}")
            return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_once()
            if self._stop_event.wait(self.interval_seconds):
                break

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="gallos-policy-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=FETCH_TIMEOUT_SECONDS + 1)
