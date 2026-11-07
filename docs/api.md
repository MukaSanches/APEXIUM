# API reference — APEXIUM source 1.0.0

## Apexium Python facade

~~~python
from apexium import Apexium
f1 = Apexium(cache=True, timeout=20, retries=2)
~~~

- cache: enables a local SQLite store under ~/.cache/apexium, or XDG_CACHE_HOME.
- cache_path: custom cache file location.
- timeout: total HTTP request timeout in seconds.
- retries: maximum transient failure retries (not guaranteed eventual success).
- openf1_headers: custom headers for authorized configurations.
- clear_cache(): erase cached responses.

Providers: f1.openf1 and f1.jolpica.

## OpenF1

Every documented endpoint has a corresponding method. The generic interface is:

~~~python
f1.openf1.query("laps", session_key=9165, driver_number=44,
                lap_duration__gte=90, ttl=0)
~~~

Methods:
car_data, championship_drivers, championship_teams, drivers,
intervals, laps, location, meetings, overtakes, pit, position, race_control,
sessions, session_result, starting_grid, stints, team_radio, weather.

Filtering: suffixes __gt, __gte, __lt, __lte, __eq convert to OpenF1 operators.
Pass lists for repeated filters. True/False is converted to lowercase query text.

## Jolpica

~~~python
f1.jolpica.races(2025)
f1.jolpica.results(2025, round=1)
f1.jolpica.qualifying(2025)
f1.jolpica.sprint(2025)
f1.jolpica.drivers(2025)
f1.jolpica.constructors(2025)
f1.jolpica.circuits(2025)
f1.jolpica.seasons()
f1.jolpica.status()
f1.jolpica.driver_standings(2025)
f1.jolpica.constructor_standings(2025)
f1.jolpica.laps(2025, 1)
f1.jolpica.pitstops(2025, 1)
f1.jolpica.driver_results("hamilton", season=2025)
f1.jolpica.all_pages("drivers", page_size=100, max_pages=20)
~~~

Results return nested race/standings records matching the upstream MRData model;
do not assume individual flat driver-result rows.

## High-level GP

~~~python
race = f1.race(2025, "Brazil")
race.meeting_key
race.session_key
race.sessions()
race.drivers()
race.results()
race.starting_grid()
race.laps(driver_number=44)
race.pits()
race.stints()
race.positions()
race.overtakes()
race.intervals()
race.telemetry(driver_number=44)
race.location(driver_number=44)
race.weather()
race.radio()
race.race_control()
race.pace_analysis()
race.pit_analysis()
race.stint_analysis()
race.position_analysis()
race.overtake_analysis()
race.data_quality()
~~~

For 1950–2022 or unavailable OpenF1 sessions use f1.jolpica directly.

## Dataset

Every provider call yields Dataset with:
- records — list of source-preserving dicts;
- source, url, fetched_at, cached — provenance;
- metadata — Jolpica pagination metadata where available;
- to_json(), to_csv(), to_pandas() (optional dependency), save(file).

Supported file extensions: .json, .csv, .parquet (requires pyarrow).

## Analytics

All 20 analysis functions accept a list of dictionaries or a Dataset. Six are shown below; see [advanced analytics](analytics.md) for all 20:
- race_pace(laps, min_laps=3, include_pit_out=False)
- pit_summary(pits)
- position_changes(positions)
- stint_summary(stints)
- overtaking_counts(overtakes)
- lap_quality(laps)

None infer unmeasured causal factors or predict future outcomes.

## JavaScript SDK

~~~js
import { Apexium, Transport, racePace, overtakeCounts } from "./sdk/javascript/index.js";
const f1 = new Apexium({ retries: 2, timeout: 20000 });
const dataset = await f1.openf1.laps({ session_key: 9165, lap_duration__gte: 90 });
const historical = await f1.jolpica.results({ season: 2025, round: 1 });
const brazil = await f1.race(2025, "Brazil").results();
console.log(dataset.rows, historical.metadata, brazil.source);
~~~

JS data envelopes use rows, source, url, fetchedAt, cached and metadata.

## Error handling

~~~python
from apexium import Apexium, APIError, ApexiumError

try:
    print(Apexium().openf1.meetings(year=2025).records)
except APIError as exc:
    print("HTTP:", exc.status, exc.url)
except ApexiumError as exc:
    print("Request or data error:", exc)
~~~

404/403 are not masked. 429/5xx may retry with backoff. Respect provider quotas.
