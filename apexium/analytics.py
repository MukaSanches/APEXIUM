"""Auditable descriptive analytics. No fabricated telemetry or probabilistic claims."""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, pstdev
from typing import Iterable


def _rows(data):
    return data.records if hasattr(data, "records") else data


def _group(data, field="driver_number"):
    groups = defaultdict(list)
    for row in _rows(data):
        if isinstance(row, dict) and row.get(field) is not None:
            groups[row[field]].append(row)
    return groups


def race_pace(laps, *, min_laps: int = 3, include_pit_out: bool = False):
    """Descriptive lap stats, NOT a tyre/fuel/traffic-adjusted ranking."""
    if min_laps < 1:
        raise ValueError("min_laps must be positive")
    output = []
    for driver, rows in _group(laps).items():
        samples = []
        for row in rows:
            value = row.get("lap_duration")
            if (value is None or isinstance(value, bool) or
                    not isinstance(value, (int, float)) or value <= 0):
                continue
            if not include_pit_out and row.get("is_pit_out_lap"):
                continue
            samples.append(float(value))
        if len(samples) < min_laps:
            continue
        output.append({
            "driver_number": driver,
            "lap_count": len(samples),
            "median_seconds": round(median(samples), 3),
            "mean_seconds": round(mean(samples), 3),
            "standard_deviation_seconds": round(pstdev(samples), 3),
            "best_seconds": round(min(samples), 3),
        })
    return sorted(output, key=lambda row: row["median_seconds"])


def pit_summary(pits):
    """Count pit entries and aggregate only non-null durations."""
    result = []
    for driver, rows in _group(pits).items():
        lanes = [float(r["lane_duration"]) for r in rows
                 if isinstance(r.get("lane_duration"), (float, int))]
        stops = [float(r["stop_duration"]) for r in rows
                 if isinstance(r.get("stop_duration"), (float, int))]
        result.append({
            "driver_number": driver,
            "pit_entries": len(rows),
            "lane_seconds_total": round(sum(lanes), 3) if lanes else None,
            "stationary_seconds_total": round(sum(stops), 3) if stops else None,
            "measured_lane_entries": len(lanes),
            "measured_stationary_stops": len(stops),
        })
    return sorted(result, key=lambda row: row["driver_number"])


def position_changes(positions):
    """Net change between first and last sampled position (not necessarily race start/finish)."""
    result = []
    for driver, rows in _group(positions).items():
        clean = [r for r in rows if isinstance(r.get("position"), int)
                 and isinstance(r.get("date"), str)]
        clean.sort(key=lambda row: row["date"])
        if not clean:
            continue
        result.append({
            "driver_number": driver,
            "first_position": clean[0]["position"],
            "last_position": clean[-1]["position"],
            "net_gain": clean[0]["position"] - clean[-1]["position"],
            "observations": len(clean),
        })
    return sorted(result, key=lambda row: row["last_position"])


def stint_summary(stints):
    result = []
    for row in _rows(stints):
        start, end = row.get("lap_start"), row.get("lap_end")
        if not isinstance(start, int) or not isinstance(end, int) or end < start:
            continue
        result.append({
            "driver_number": row.get("driver_number"),
            "compound": row.get("compound"),
            "stint_number": row.get("stint_number"),
            "laps": end - start + 1,
            "tyre_age_at_start": row.get("tyre_age_at_start"),
        })
    return sorted(result, key=lambda x: (x["driver_number"] or 0, x["stint_number"] or 0))


def overtaking_counts(overtakes):
    """Includes position swaps in pits and penalties, according to OpenF1 coverage."""
    counts = defaultdict(int)
    for row in _rows(overtakes):
        driver = row.get("overtaking_driver_number")
        if driver is not None:
            counts[driver] += 1
    return sorted(
        [{"driver_number": d, "recorded_position_swaps": n} for d, n in counts.items()],
        key=lambda x: -x["recorded_position_swaps"],
    )


def lap_quality(laps):
    """Surface potential quality issues; never silently edit upstream data."""
    rows = list(_rows(laps))
    invalid = [r for r in rows if
               r.get("lap_duration") is not None and
               (not isinstance(r["lap_duration"], (int, float)) or
                isinstance(r["lap_duration"], bool) or r["lap_duration"] <= 0)]
    keys = [(r.get("driver_number"), r.get("lap_number"), r.get("session_key"))
            for r in rows]
    return {
        "records": len(rows),
        "missing_lap_duration": sum(r.get("lap_duration") is None for r in rows),
        "invalid_lap_duration": len(invalid),
        "duplicate_driver_lap_session": len(keys) - len(set(keys)),
        "missing_driver_number": sum(r.get("driver_number") is None for r in rows),
    }
