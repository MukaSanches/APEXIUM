"""HTTP, SQLite caching and retry logic with no runtime dependencies."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .dataset import Dataset


class ApexiumError(RuntimeError):
    """Errors raised by APEXIUM."""


class APIError(ApexiumError):
    def __init__(self, status: int, url: str, detail: str = ""):
        self.status = status
        self.url = url
        super().__init__(f"HTTP {status}: {detail[:200]} ({url})")


class SQLiteCache:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS responses "
                "(url TEXT PRIMARY KEY, expires REAL NOT NULL, payload TEXT NOT NULL, "
                "fetched_at TEXT NOT NULL)"
            )

    def get(self, url: str) -> tuple[object, str] | None:
        with self._lock, sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT payload, fetched_at FROM responses WHERE url = ? AND expires > ?",
                (url, time.time()),
            ).fetchone()
        return (json.loads(row[0]), row[1]) if row else None

    def set(self, url: str, payload: object, ttl: int, fetched_at: str) -> None:
        if ttl <= 0:
            return
        with self._lock, sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT OR REPLACE INTO responses (url, expires, payload, fetched_at) "
                "VALUES (?, ?, ?, ?)",
                (url, time.time() + ttl, json.dumps(payload), fetched_at),
            )

    def clear(self) -> None:
        with self._lock, sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM responses")


class Transport:
    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        cache: SQLiteCache | None = None,
        timeout: float = 20,
        retries: int = 2,
        min_interval: float = 0.35,
        headers: dict[str, str] | None = None,
        opener=None,
    ):
        if timeout <= 0 or retries < 0 or min_interval < 0:
            raise ValueError("Invalid HTTP configuration")
        self.cache = cache
        self.timeout = timeout
        self.retries = retries
        self.min_interval = min_interval
        self.headers = {"User-Agent": "apexium-f1/1.0 (+https://github.com/MukaSanches/APEXIUM)",
                        "Accept": "application/json", **(headers or {})}
        self.opener = opener or urlopen
        self._lock = threading.Lock()
        self._last = 0.0

    def get(self, url: str, *, source: str, ttl: int = 21600) -> Dataset:
        if ttl < 0:
            raise ValueError("ttl cannot be negative")
        if self.cache and ttl:
            cached = self.cache.get(url)
            if cached is not None:
                payload, fetched_at = cached
                return self._dataset(payload, source, url, fetched_at, True)
        for attempt in range(self.retries + 1):
            self._throttle()
            try:
                request = Request(url, headers=self.headers)
                with self.opener(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    stamp = datetime.now(timezone.utc).isoformat()
                    if self.cache:
                        self.cache.set(url, payload, ttl, stamp)
                    return self._dataset(payload, source, url, stamp, False)
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code not in self.RETRY_STATUSES or attempt >= self.retries:
                    raise APIError(exc.code, url, detail) from exc
                delay = _retry_after(exc.headers.get("Retry-After") if exc.headers else None)
                time.sleep(delay if delay is not None else min(2 ** attempt, 8))
            except (URLError, TimeoutError, OSError) as exc:
                if attempt >= self.retries:
                    raise ApexiumError(f"Network failure for {url}: {exc}") from exc
                time.sleep(min(2 ** attempt, 8))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ApexiumError(f"Invalid JSON from {url}") from exc
        raise AssertionError("unreachable")

    @staticmethod
    def _dataset(payload: object, source: str, url: str, stamp: str, cached: bool) -> Dataset:
        if source == "openf1":
            if not isinstance(payload, list):
                raise ApexiumError("OpenF1 returned an unexpected JSON shape")
            rows = payload
            metadata = {}
        elif source == "jolpica":
            if not isinstance(payload, dict) or not isinstance(payload.get("MRData"), dict):
                raise ApexiumError("Jolpica returned an unexpected JSON shape")
            body = payload["MRData"]
            rows = _jolpica_rows(body)
            metadata = {
                key: body.get(key)
                for key in ("limit", "offset", "total", "series")
                if key in body
            }
        else:
            raise ValueError("Unknown data source")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ApexiumError(f"{source} returned an unexpected data structure")
        return Dataset(rows, source, url, stamp, cached, metadata)

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = self.min_interval - (now - self._last)
            if delta > 0:
                time.sleep(delta)
            self._last = time.monotonic()


def _jolpica_rows(mrdata: dict) -> list:
    for key, value in mrdata.items():
        if key.endswith("Table") and isinstance(value, dict):
            for field in ("Races", "StandingsLists", "Drivers", "Constructors",
                          "Circuits", "Seasons", "Status"):
                if isinstance(value.get(field), list):
                    return value[field]
    return []


def _retry_after(header: str | None) -> float | None:
    if not header:
        return None
    try:
        return min(max(float(header), 0.0), 30.0)
    except ValueError:
        try:
            value = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
            return min(max(value, 0.0), 30.0)
        except (TypeError, ValueError, OverflowError):
            return None


def default_cache_path() -> Path:
    root = os.getenv("XDG_CACHE_HOME")
    return (Path(root) if root else Path.home() / ".cache") / "apexium" / "responses.sqlite3"
