"""All documented OpenF1 REST resource families, including range filtering."""
from __future__ import annotations

from urllib.parse import urlencode

from .dataset import Dataset
from .transport import Transport

ENDPOINTS = (
    "car_data", "championship_drivers", "championship_teams", "drivers",
    "intervals", "laps", "location", "meetings", "overtakes", "pit", "position",
    "race_control", "sessions", "session_result", "starting_grid", "stints",
    "team_radio", "weather",
)
OPERATORS = {
    "eq": "=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
}


class OpenF1:
    """Documented endpoints are available as named methods or through query()."""

    def __init__(self, transport: Transport, base_url: str = "https://api.openf1.org/v1"):
        self.transport = transport
        self.base_url = base_url.rstrip("/")

    def query(self, endpoint: str, *, ttl: int | None = None, **filters) -> Dataset:
        if endpoint not in ENDPOINTS:
            raise ValueError(f"Unknown OpenF1 endpoint: {endpoint}")
        params = []
        for name, value in filters.items():
            parts = name.rsplit("__", 1)
            if len(parts) == 2 and parts[1] in OPERATORS:
                name = parts[0] + OPERATORS[parts[1]]
            if not name or not all(c.isalnum() or c in "_><=" for c in name):
                raise ValueError(f"Invalid filter name: {name}")
            if value is None:
                continue
            if isinstance(value, bool):
                value = str(value).lower()
            if isinstance(value, (list, tuple)):
                params.extend((name, v) for v in value)
            else:
                params.append((name, value))
        query = urlencode(sorted(params), doseq=True)
        url = f"{self.base_url}/{endpoint}" + (f"?{query}" if query else "")
        cache_ttl = 10 if any(str(v) == "latest" for _, v in params) else 21600
        return self.transport.get(url, source="openf1", ttl=cache_ttl if ttl is None else ttl)


def _endpoint_method(endpoint):
    def method(self, **filters):
        return self.query(endpoint, **filters)
    method.__name__ = endpoint
    method.__doc__ = f"Fetch OpenF1 /{endpoint} using optional API filters."
    return method


for _name in ENDPOINTS:
    setattr(OpenF1, _name, _endpoint_method(_name))
