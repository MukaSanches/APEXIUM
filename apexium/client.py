"""High-level facade for historical sessions and provider-specific access."""
from __future__ import annotations

import unicodedata
from pathlib import Path

from .analytics import (
    lap_quality, overtaking_counts, pit_summary, position_changes, race_pace,
    stint_summary,
)
from .jolpica import Jolpica
from .openf1 import OpenF1
from .transport import ApexiumError, SQLiteCache, Transport, default_cache_path


def _normalize(value) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    return "".join(c for c in text if not unicodedata.combining(c))


class Apexium:
    """One entry point to real OpenF1 and Jolpica resources."""

    def __init__(
        self,
        *,
        cache: bool = True,
        cache_path: str | Path | None = None,
        timeout: float = 20,
        retries: int = 2,
        openf1_headers: dict[str, str] | None = None,
    ):
        self.cache = SQLiteCache(cache_path or default_cache_path()) if cache else None
        self.openf1 = OpenF1(Transport(
            cache=self.cache, timeout=timeout, retries=retries,
            min_interval=0.36, headers=openf1_headers,
        ))
        self.jolpica = Jolpica(Transport(
            cache=self.cache, timeout=timeout, retries=retries,
            min_interval=0.26,
        ))

    def race(self, year: int, grand_prix: str) -> Race:
        """Select an OpenF1 Grand Prix (2023 onward) by country, name or location."""
        if year < 2023:
            raise ValueError("OpenF1 high-level race access requires 2023 or newer; use jolpica for 1950+")
        if not grand_prix or not grand_prix.strip():
            raise ValueError("grand_prix cannot be empty")
        return Race(self.openf1, year, grand_prix)

    def clear_cache(self) -> None:
        if self.cache is not None:
            self.cache.clear()


class Race:
    """Lazy OpenF1 race context; session and meeting keys are resolved once."""

    def __init__(self, provider: OpenF1, year: int, grand_prix: str):
        self.provider = provider
        self.year = year
        self.grand_prix = grand_prix
        self._meeting = None
        self._race_session = None

    @property
    def meeting(self) -> dict:
        if self._meeting is None:
            matches = self.provider.meetings(year=self.year).records
            needle = _normalize(self.grand_prix)
            exact = [item for item in matches if
                     needle in {_normalize(item.get(k, "")) for k in
                                ("meeting_name", "country_name", "location", "circuit_short_name")}]
            partial = [item for item in matches if any(
                needle in _normalize(item.get(k, "")) for k in
                ("meeting_name", "country_name", "location", "circuit_short_name")
            )]
            candidates = exact or partial
            if not candidates:
                raise ApexiumError(
                    f"Grand Prix {self.grand_prix!r} not found for {self.year}; "
                    "check available meetings via client.openf1.meetings(year=...)"
                )
            if len(candidates) > 1:
                raise ApexiumError("Ambiguous Grand Prix; supply a more specific location or name")
            self._meeting = candidates[0]
        return self._meeting

    @property
    def meeting_key(self) -> int:
        return self.meeting["meeting_key"]

    @property
    def session(self) -> dict:
        if self._race_session is None:
            sessions = self.provider.sessions(meeting_key=self.meeting_key).records
            races = [row for row in sessions if row.get("session_name") == "Race"]
            if not races:
                races = [row for row in sessions if row.get("session_type") == "Race"
                         and "Sprint" not in row.get("session_name", "")]
            if not races:
                raise ApexiumError(f"No race session currently available for {self.grand_prix}")
            self._race_session = races[0]
        return self._race_session

    @property
    def session_key(self) -> int:
        return self.session["session_key"]

    def sessions(self):
        return self.provider.sessions(meeting_key=self.meeting_key)

    def _fetch(self, resource: str, **filters):
        filters.setdefault("session_key", self.session_key)
        return self.provider.query(resource, **filters)

    def drivers(self, **filters):
        return self._fetch("drivers", **filters)

    def results(self, **filters):
        return self._fetch("session_result", **filters)

    def starting_grid(self, **filters):
        return self._fetch("starting_grid", **filters)

    def laps(self, **filters):
        return self._fetch("laps", **filters)

    def stints(self, **filters):
        return self._fetch("stints", **filters)

    def pits(self, **filters):
        return self._fetch("pit", **filters)

    def positions(self, **filters):
        return self._fetch("position", **filters)

    def overtakes(self, **filters):
        return self._fetch("overtakes", **filters)

    def intervals(self, **filters):
        return self._fetch("intervals", **filters)

    def telemetry(self, **filters):
        return self._fetch("car_data", **filters)

    def location(self, **filters):
        return self._fetch("location", **filters)

    def weather(self, **filters):
        return self._fetch("weather", **filters)

    def radio(self, **filters):
        return self._fetch("team_radio", **filters)

    def race_control(self, **filters):
        return self._fetch("race_control", **filters)

    def pace_analysis(self, **filters):
        return race_pace(self.laps(**filters))

    def pit_analysis(self, **filters):
        return pit_summary(self.pits(**filters))

    def stint_analysis(self, **filters):
        return stint_summary(self.stints(**filters))

    def position_analysis(self, **filters):
        return position_changes(self.positions(**filters))

    def overtake_analysis(self, **filters):
        return overtaking_counts(self.overtakes(**filters))

    def data_quality(self, **filters):
        return lap_quality(self.laps(**filters))
