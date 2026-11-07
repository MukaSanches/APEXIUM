"""Jolpica/Ergast-compatible historical Formula 1 API adapter."""
from __future__ import annotations

import re
from urllib.parse import urlencode

from .dataset import Dataset
from .transport import Transport

RESOURCES = {
    "races", "results", "qualifying", "sprint", "drivers", "constructors",
    "circuits", "seasons", "status", "driverstandings", "constructorstandings",
    "laps", "pitstops",
}
VALID_PART = re.compile(r"^[A-Za-z0-9_-]+$")


def _part(value) -> str:
    part = str(value)
    if not VALID_PART.fullmatch(part):
        raise ValueError(f"Invalid path component: {part}")
    return part


class Jolpica:
    def __init__(self, transport: Transport, base_url: str = "https://api.jolpi.ca/ergast/f1"):
        self.transport = transport
        self.base_url = base_url.rstrip("/")

    def query(self, resource: str, *, season=None, round=None,
              driver=None, constructor=None, limit: int = 100,
              offset: int = 0, ttl: int = 21600) -> Dataset:
        if resource not in RESOURCES:
            raise ValueError(f"Unknown Jolpica resource: {resource}")
        if limit < 1 or limit > 2000 or offset < 0:
            raise ValueError("limit must be between 1 and 2000; offset cannot be negative")
        path = []
        if season is not None:
            path.append(_part(season))
        if round is not None:
            if season is None:
                raise ValueError("round requires season")
            path.append(_part(round))
        if driver is not None:
            path.extend(("drivers", _part(driver)))
        if constructor is not None:
            path.extend(("constructors", _part(constructor)))
        path.append(_part(resource) + ".json")
        url = self.base_url + "/" + "/".join(path) + "?" + urlencode(
            {"limit": limit, "offset": offset}
        )
        return self.transport.get(url, source="jolpica", ttl=ttl)

    def races(self, season=None, **kwargs):
        return self.query("races", season=season, **kwargs)

    def results(self, season=None, round=None, **kwargs):
        return self.query("results", season=season, round=round, **kwargs)

    def qualifying(self, season=None, round=None, **kwargs):
        return self.query("qualifying", season=season, round=round, **kwargs)

    def sprint(self, season=None, round=None, **kwargs):
        return self.query("sprint", season=season, round=round, **kwargs)

    def drivers(self, season=None, **kwargs):
        return self.query("drivers", season=season, **kwargs)

    def constructors(self, season=None, **kwargs):
        return self.query("constructors", season=season, **kwargs)

    def circuits(self, season=None, **kwargs):
        return self.query("circuits", season=season, **kwargs)

    def seasons(self, **kwargs):
        return self.query("seasons", **kwargs)

    def status(self, **kwargs):
        return self.query("status", **kwargs)

    def driver_standings(self, season, **kwargs):
        return self.query("driverstandings", season=season, **kwargs)

    def constructor_standings(self, season, **kwargs):
        return self.query("constructorstandings", season=season, **kwargs)

    def laps(self, season, round, **kwargs):
        return self.query("laps", season=season, round=round, **kwargs)

    def pitstops(self, season, round, **kwargs):
        return self.query("pitstops", season=season, round=round, **kwargs)

    def driver_results(self, driver: str, season=None, **kwargs):
        return self.query("results", season=season, driver=driver, **kwargs)

    def all_pages(self, resource: str, *, page_size: int = 100,
                  max_pages: int = 10, **kwargs) -> Dataset:
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        rows, first = [], None
        offset = int(kwargs.pop("offset", 0))
        for _ in range(max_pages):
            current = self.query(resource, limit=page_size, offset=offset, **kwargs)
            first = first or current
            rows.extend(current.records)
            total = int(current.metadata.get("total") or 0)
            offset += len(current.records)
            if not current.records or (total and offset >= total):
                break
        assert first is not None
        return Dataset(rows, "jolpica", first.url, first.fetched_at, first.cached,
                       {**first.metadata, "returned": len(rows), "next_offset": offset})
