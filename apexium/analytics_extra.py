"""Additional deterministic motorsport analytics built exclusively from observed data.

These functions are descriptive, not causal inference or race prediction. No
missing timing/telemetry is reconstructed or represented as measured.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from math import isfinite
from statistics import mean, median, pstdev


def _rows(data):
    return data.records if hasattr(data, "records") else data


def _valid(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(value)


def _group(data, field="driver_number"):
    grouped = defaultdict(list)
    for row in _rows(data):
        if isinstance(row, dict) and row.get(field) is not None:
            grouped[row[field]].append(row)
    return grouped


def fastest_laps(laps):
    """Best observed valid total lap per driver."""
    output = []
    for driver, rows in _group(laps).items():
        eligible = [r for r in rows if _valid(r.get("lap_duration"))
                    and r["lap_duration"] > 0 and not r.get("is_pit_out_lap")]
        if eligible:
            best = min(eligible, key=lambda r: r["lap_duration"])
            output.append({"driver_number": driver, "lap_number": best.get("lap_number"),
                           "lap_seconds": best["lap_duration"],
                           "valid_laps": len(eligible)})
    return sorted(output, key=lambda row: row["lap_seconds"])


def ideal_laps(laps):
    """Sum independently observed best three sectors for each driver.

    This is a theoretical best-sector sum, NOT a completed feasible lap.
    """
    output = []
    fields = ("duration_sector_1", "duration_sector_2", "duration_sector_3")
    for driver, rows in _group(laps).items():
        best = []
        for field in fields:
            times = [r[field] for r in rows if _valid(r.get(field)) and r[field] > 0]
            if not times:
                break
            best.append(min(times))
        if len(best) == 3:
            actual = [r["lap_duration"] for r in rows if _valid(r.get("lap_duration"))
                      and r["lap_duration"] > 0 and not r.get("is_pit_out_lap")]
            output.append({
                "driver_number": driver,
                "best_sector_1_seconds": best[0],
                "best_sector_2_seconds": best[1],
                "best_sector_3_seconds": best[2],
                "ideal_seconds": round(sum(best), 3),
                "best_recorded_seconds": min(actual) if actual else None,
            })
    return sorted(output, key=lambda r: r["ideal_seconds"])


def sector_pace(laps):
    """Median of measured individual sector times, grouped by driver."""
    output = []
    for driver, rows in _group(laps).items():
        entry = {"driver_number": driver}
        for idx in (1, 2, 3):
            field = f"duration_sector_{idx}"
            times = [float(r[field]) for r in rows if
                     _valid(r.get(field)) and r[field] > 0]
            entry[f"sector_{idx}_median_seconds"] = round(median(times), 3) if times else None
            entry[f"sector_{idx}_samples"] = len(times)
        output.append(entry)
    return sorted(output, key=lambda r: r["driver_number"])


def lap_trends(laps, *, min_laps: int = 4):
    """Ordinary least-squares seconds/lap trend, UNADJUSTED for confounders."""
    if min_laps < 2:
        raise ValueError("min_laps must be at least two")
    output = []
    for driver, rows in _group(laps).items():
        xy = [(float(r["lap_number"]), float(r["lap_duration"])) for r in rows
              if _valid(r.get("lap_number")) and _valid(r.get("lap_duration"))
              and r["lap_duration"] > 0 and not r.get("is_pit_out_lap")]
        if len(xy) < min_laps:
            continue
        xavg = mean(p[0] for p in xy)
        yavg = mean(p[1] for p in xy)
        denom = sum((x-xavg)**2 for x, _ in xy)
        if not denom:
            continue
        slope = sum((x-xavg)*(y-yavg) for x, y in xy) / denom
        output.append({"driver_number": driver, "samples": len(xy),
                       "slope_seconds_per_lap": round(slope, 6)})
    return sorted(output, key=lambda r: r["slope_seconds_per_lap"])


def compound_pace(laps, stints):
    """Median observed lap durations by driver and tyre compound (no tyre/fuel adjustment)."""
    stints_by_driver = _group(stints)
    samples = defaultdict(list)
    for lap in _rows(laps):
        driver = lap.get("driver_number")
        num = lap.get("lap_number")
        time = lap.get("lap_duration")
        if not (_valid(num) and _valid(time) and time > 0) or lap.get("is_pit_out_lap"):
            continue
        matches = [s for s in stints_by_driver.get(driver, []) if
                   _valid(s.get("lap_start")) and _valid(s.get("lap_end"))
                   and s["lap_start"] <= num <= s["lap_end"]]
        if len(matches) == 1 and matches[0].get("compound"):
            samples[(driver, matches[0]["compound"])].append(float(time))
    return sorted(({"driver_number": driver, "compound": compound,
                    "laps": len(times), "median_seconds": round(median(times), 3)}
                   for (driver, compound), times in samples.items()),
                  key=lambda r: (r["driver_number"], r["compound"]))


def stint_strategies(stints):
    """Stint compound order and total lap count for each driver."""
    output = []
    for driver, rows in _group(stints).items():
        valid = sorted((r for r in rows if _valid(r.get("lap_start")) and
                        _valid(r.get("lap_end")) and r["lap_end"] >= r["lap_start"]),
                       key=lambda r: (r["lap_start"], r.get("stint_number") or 0))
        output.append({
            "driver_number": driver,
            "compounds": [r.get("compound") for r in valid],
            "stint_laps": [int(r["lap_end"]-r["lap_start"]+1) for r in valid],
            "stint_count": len(valid),
        })
    return sorted(output, key=lambda r: r["driver_number"])


def pit_window_histogram(pits):
    """How many reported pit entries occurred on each lap, across drivers."""
    counts = Counter(r["lap_number"] for r in _rows(pits)
                     if _valid(r.get("lap_number")) and r["lap_number"] >= 1)
    return [{"lap_number": lap, "pit_entries": n} for lap, n in sorted(counts.items())]


def speed_summary(car_data):
    """Sample-weighted min/mean/max reported km/h; NOT time- or distance-weighted."""
    output = []
    for driver, rows in _group(car_data).items():
        speeds = [float(r["speed"]) for r in rows if
                  _valid(r.get("speed")) and r["speed"] >= 0]
        if not speeds:
            continue
        output.append({
            "driver_number": driver, "samples": len(speeds),
            "minimum_kmh": min(speeds), "mean_kmh": round(mean(speeds), 3),
            "maximum_kmh": max(speeds),
        })
    return sorted(output, key=lambda r: -r["maximum_kmh"])


def throttle_brake_summary(car_data):
    """Percentage of telemetry samples with full throttle or brake engaged."""
    output = []
    for driver, rows in _group(car_data).items():
        throttle = [float(r["throttle"]) for r in rows if
                    _valid(r.get("throttle")) and 0 <= r["throttle"] <= 100]
        brake = [float(r["brake"]) for r in rows if _valid(r.get("brake"))]
        output.append({
            "driver_number": driver,
            "throttle_samples": len(throttle), "brake_samples": len(brake),
            "full_throttle_sample_pct": round(100 * sum(t >= 95 for t in throttle) /
                                              len(throttle), 2) if throttle else None,
            "brake_engaged_sample_pct": round(100 * sum(b > 0 for b in brake) /
                                               len(brake), 2) if brake else None,
        })
    return sorted(output, key=lambda r: r["driver_number"])


def drs_code_summary(car_data):
    """Sample ratio of DRS codes 10/12/14; code semantics depend on era/provider."""
    active_codes = {10, 12, 14}
    output = []
    for driver, rows in _group(car_data).items():
        codes = [r["drs"] for r in rows if isinstance(r.get("drs"), int)
                 and not isinstance(r["drs"], bool)]
        output.append({
            "driver_number": driver, "samples_with_drs_code": len(codes),
            "code_10_12_14_pct": round(100 * sum(x in active_codes for x in codes) /
                                       len(codes), 2) if codes else None,
        })
    return sorted(output, key=lambda r: r["driver_number"])


def weather_summary(weather):
    """Arithmetic sample means, not exact duration-weighted weather conditions."""
    rows = list(_rows(weather))
    result = {"samples": len(rows)}
    for field in ("air_temperature", "track_temperature", "humidity",
                  "wind_speed", "wind_direction", "air_pressure"):
        vals = [float(r[field]) for r in rows if _valid(r.get(field))]
        result[f"mean_{field}"] = round(mean(vals), 3) if vals else None
        result[f"samples_{field}"] = len(vals)
    result["rainfall_reported_samples"] = sum(bool(r.get("rainfall")) for r in rows)
    return result


def race_control_summary(events):
    """Counts *reported messages*, not unique incidents or safety-car periods."""
    rows = list(_rows(events))
    by_category = Counter(str(r.get("category") or "UNKNOWN") for r in rows)
    by_flag = Counter(str(r["flag"]) for r in rows if r.get("flag"))
    return {
        "messages": len(rows),
        "by_category": dict(sorted(by_category.items())),
        "by_flag": dict(sorted(by_flag.items())),
    }


def lap_deltas(laps, driver_a: int, driver_b: int):
    """Aligned lap numbers; positive delta means driver_a was slower that lap."""
    by_driver = _group(laps)
    def valid_laps(number):
        return {r["lap_number"]: float(r["lap_duration"]) for r in by_driver.get(number, [])
                if _valid(r.get("lap_number")) and _valid(r.get("lap_duration"))
                and r["lap_duration"] > 0 and not r.get("is_pit_out_lap")}
    a, b = valid_laps(driver_a), valid_laps(driver_b)
    return [{"lap_number": lap, "driver_a": driver_a, "driver_b": driver_b,
             "delta_a_minus_b_seconds": round(a[lap]-b[lap], 3)}
            for lap in sorted(a.keys() & b.keys())]


def position_trajectory(positions, driver: int):
    """Observed change points for one driver, with no interpolation."""
    valid = [row for row in _rows(positions) if row.get("driver_number") == driver
             and isinstance(row.get("position"), int)
             and isinstance(row.get("date"), str)]
    valid.sort(key=lambda row: row["date"])
    output = []
    previous = None
    for row in valid:
        if row["position"] != previous:
            output.append({"date": row["date"], "driver_number": driver,
                           "position": row["position"]})
            previous = row["position"]
    return output
