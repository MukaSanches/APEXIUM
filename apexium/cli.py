"""The apexium CLI: access real F1 datasets from any terminal."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .client import Apexium
from .jolpica import RESOURCES
from .openf1 import ENDPOINTS


def _value(raw: str):
    if raw.isdecimal():
        return int(raw)
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="apexium", description="Explore real Formula 1 datasets."
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="source", required=True)
    openf1 = sub.add_parser("openf1", help="Query one of 18 OpenF1 resources")
    openf1.add_argument("resource", choices=ENDPOINTS)
    openf1.add_argument("--filter", action="append", default=[], metavar="FIELD=VALUE",
                        help="Repeatable query filter (e.g. session_key=9165)")
    openf1.add_argument("--output", help="Write .json, .csv or .parquet")
    jolpica = sub.add_parser("jolpica", help="Query historical race and standings data")
    jolpica.add_argument("resource", choices=sorted(RESOURCES))
    jolpica.add_argument("--season")
    jolpica.add_argument("--round")
    jolpica.add_argument("--limit", type=int, default=100)
    jolpica.add_argument("--output")
    race = sub.add_parser("race", help="Select a Grand Prix by country or name")
    race.add_argument("year", type=int)
    race.add_argument("grand_prix")
    race.add_argument("resource", choices=(
        "results", "drivers", "laps", "pits", "stints", "positions", "overtakes",
        "weather", "radio", "race_control", "pace_analysis", "pit_analysis",
        "stint_analysis", "position_analysis", "overtake_analysis", "data_quality",
    ))
    race.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        api = Apexium()
        if args.source == "openf1":
            filters = {}
            for pair in args.filter:
                if "=" not in pair:
                    parser.error("--filter must be FIELD=VALUE")
                name, value = pair.split("=", 1)
                filters[name] = _value(value)
            result = api.openf1.query(args.resource, **filters)
        elif args.source == "jolpica":
            result = api.jolpica.query(
                args.resource, season=args.season, round=args.round, limit=args.limit,
            )
        else:
            selected = api.race(args.year, args.grand_prix)
            result = getattr(selected, args.resource)()
        if args.output:
            if hasattr(result, "save"):
                output = result.save(args.output)
            else:
                from .dataset import Dataset
                from datetime import datetime, timezone
                rows = result if isinstance(result, list) else [result]
                output = Dataset(rows, "apexium", "analysis",
                                 datetime.now(timezone.utc).isoformat()).save(args.output)
            print(output)
        else:
            print(json.dumps(
                result.records if hasattr(result, "records") else result,
                indent=2, ensure_ascii=False,
            ))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"APEXIUM error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
