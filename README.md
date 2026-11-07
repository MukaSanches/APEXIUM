# APEXIUM
### Real racing data. One developer platform.

[![Test suite](https://github.com/MukaSanches/APEXIUM/actions/workflows/ci.yml/badge.svg)](https://github.com/MukaSanches/APEXIUM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-Node%2018%2B-F7DF1E)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Contributions](https://img.shields.io/badge/contributions-welcome-brightgreen)](CONTRIBUTING.md)

**APEXIUM** is an open-source, cross-language developer toolkit for Formula 1 data. Fetch historical race results, explore telemetry, analyze racing laps, export datasets and build applications using a consistent interface.

**Design premise:** Make a useful application with real data in minutes, preserve source attribution, and never imply a model has measured something that it only estimated.

> **Release status:** Source tree version 1.0.0, **alpha**. Not published to PyPI or npm. The repository includes offline tests; real-upstream integration and performance claims must be verified separately before production deployment. It is not the world's largest library, and no adoption record has been established.

**Languages:** Python 3.10+ (zero mandatory runtime dependencies) and JavaScript ESM for Node.js 18+ / modern browsers (zero dependencies).

[Quick start](#get-running-in-60-seconds) · [Features](#capabilities) · [API guide](docs/api.md) · [Architecture](docs/architecture.md) · [Português](docs/README.pt-BR.md) · [Contributing](CONTRIBUTING.md)

---

## APEXIUM Studio — use no navegador (sem programação)

O repositório também inclui um **site e aplicativo instalável (PWA)** para Windows, macOS, Linux, Android e iOS, sem exigir cadastro, terminal ou Python. O público pode consultar dados reais de Fórmula 1, rankings, calendário, gráficos de telemetria e **20 análises** com poucos cliques.

**Endereço previsto após o GitHub Pages estar habilitado e o deploy passar:** https://mukasanches.github.io/APEXIUM/ — **não assuma que já está publicado.** Se a publicação ainda não estiver ativa, veja [como ativar o site e instalar o app](docs/site.md).

| Tela | O que faz |
| --- | --- |
| Visão geral | Temporada, GP, classificação e próximas etapas |
| Campeonato | Ranking de pilotos e construtores |
| Calendário | Datas, circuitos e horários no fuso do visitante |
| Race Lab | 20 análises sobre ritmo, boxes, pneus, setores, condições e posições |
| Telemetry Studio | Gráficos de velocidade, acelerador, freio e RPM por volta |
| Data Explorer | Consulta a endpoints e exportação CSV/JSON |
| Instalação PWA | Ícone e modo de aplicativo em navegadores compatíveis |

**Testes do aplicativo:**

```bash
node --test tests/site.test.mjs
node scripts/build-site.mjs
node scripts/serve-site.mjs
# Abrir http://127.0.0.1:4173/
```

A interface utiliza respostas diretas das APIs e suas condições de uso. Os testes da UI com dados simulados **não** demonstram disponibilidade ininterrupta das APIs reais; não há dados de assinatura em tempo real nem dados inventados.

[Documentação de usuário](docs/site.md) · [Código do site](site/) · [Testes de navegação](tests/browser_smoke.py) · [Deploy Pages](.github/workflows/site.yml)

---

## Get running in 60 seconds

Clone the repository:

~~~bash
git clone https://github.com/MukaSanches/APEXIUM.git
cd APEXIUM
python -m pip install -e .
~~~

### Python: real session data

~~~python
from apexium import Apexium

f1 = Apexium()

# Public historical OpenF1 meeting list.
meetings = f1.openf1.meetings(year=2025)
print(meetings.records[:2])

# Historical results from the Jolpica API (1950+).
standings = f1.jolpica.driver_standings(2025)
print(standings.records[0]["DriverStandings"][:3])

# High-level OpenF1 race convenience wrapper (2023+).
brazil = f1.race(2025, "Brazil")
print(brazil.results().records[:3])
print(brazil.pace_analysis()[:5])
~~~

### JavaScript: Node.js or browser

The JavaScript package is currently distributed as **source**, not via npm.

~~~js
import { Apexium, racePace } from "./sdk/javascript/index.js";

const f1 = new Apexium();
const { rows: meetings } = await f1.openf1.meetings({ year: 2025 });
console.log(meetings.length);

const laps = await f1.race(2025, "Brazil").laps();
console.log(racePace(laps));
~~~

### Terminal: no application required

~~~bash
apexium openf1 meetings --filter year=2025
apexium openf1 laps --filter session_key=9165 --filter driver_number=44 --output laps.csv
apexium jolpica driverstandings --season 2025 --output standings.json
apexium race 2025 Brazil pace_analysis --output pace.csv
~~~

CLI commands contact public third-party APIs unless a matching unexpired response is cached.

---

## Capabilities

| Area | Available in the source release | Interface |
| --- | --- | --- |
| OpenF1 data | **18** documented resource families | Python + JavaScript |
| Jolpica/Ergast history | **13** resource families | Python + JavaScript |
| High-level race selection | Resolve meeting, session and session-key | Python + JavaScript |
| Statistical analysis | **20** auditable Python functions | Python |
| JavaScript analysis | Lap summary and recorded position swaps | JavaScript |
| Cache | SQLite persistence (Python), memory TTL (JavaScript) | Both |
| Reliability | Timeouts, retry of transient HTTP failures, API errors | Both |
| Data provenance | Upstream URL, source, fetch time, cache status | Both |
| Data export | JSON, CSV, optional Parquet | Python |
| Optional integration | FastF1 Session loader | Python |
| CLI | Resource fetching, optional export, analysis | Python |
| Testing | Offline Python and Node test suites, GitHub Actions | Both |

### OpenF1 resources (18)

| Competition | Telemetry and positions | Events and conditions |
| --- | --- | --- |
| meetings | car_data | race_control |
| sessions | location | overtakes |
| drivers | intervals | pit |
| championship_drivers (beta) | position | team_radio |
| championship_teams (beta) | laps | weather |
| session_result | starting_grid | stints |

The OpenF1 adapter exposes a method for each resource, and a generic query interface:

~~~python
# Driver 44's laps of at least 90 seconds in a known historical session.
laps = f1.openf1.laps(
    session_key=9165,
    driver_number=44,
    lap_duration__gte=90,
)
print(laps.source, laps.url, len(laps.records))
~~~

Supported range suffixes: **__gt**, **__gte**, **__lt**, **__lte** and **__eq**. Repeat a filter value by passing a list. These operations map to upstream API parameters.

### Jolpica historical resources (13)

- races, results, qualifying, sprint
- drivers, constructors, circuits, seasons, status
- driverstandings, constructorstandings, laps, pitstops

~~~python
# Entire year's results are provided as nested race records.
races = f1.jolpica.results(2025)
for race in races.records:
    print(race.get("raceName"), len(race.get("Results", [])))

# Stream pages sensibly, respecting upstream limits.
all_drivers = f1.jolpica.all_pages(
    "drivers", page_size=100, max_pages=20
)
~~~

### 20 descriptive analysis functions

The initial six core functions plus fourteen advanced calculations cover:
- Fastest laps and theoretical ideal-sector sums.
- Sector pace and unadjusted lap-time trends.
- Observed pace by tyre compound and complete stint sequences.
- Pit-stop lap distributions.
- Maximum/mean/minimum observed speeds.
- Throttle, brake and DRS-code sample ratios.
- Weather summaries and Race Control message counts.
- Driver-to-driver lap deltas and position change points.

See [advanced analytics](docs/analytics.md) for formulas, limitations and examples.

### Analytics that do not fabricate measurements

~~~python
from apexium.analytics import (
    race_pace,
    pit_summary,
    position_changes,
    stint_summary,
    overtaking_counts,
    lap_quality,
)

race = f1.race(2025, "Brazil")
laps = race.laps()
print(race_pace(laps))  # Observed median/mean/std. Not fuel-corrected.
print(lap_quality(laps))  # Potentially missing/duplicate records.
print(pit_summary(race.pits()))
print(stint_summary(race.stints()))
print(position_changes(race.positions()))
print(overtaking_counts(race.overtakes()))
~~~

**Interpret results carefully:**
- Lap pace is descriptive, **not adjusted** for tyres, fuel, traffic, or track evolution.
- OpenF1 recorded overtakes can include pit-related position changes and penalties; they do not exclusively count on-track passes.
- First-to-last positions reflect the available sampling window, not necessarily official grid versus final classification.
- Team-radio coverage is partial, especially in 2026; missing data does not indicate absence of radio traffic.
- Pit-lane durations are not the same metric as stationary wheel-change time.

### Export and dataframe compatibility

~~~python
laps = f1.race(2025, "Brazil").laps(driver_number=44)
laps.save("exports/brazil_2025_44.json")
laps.save("exports/brazil_2025_44.csv")

# Optional: pip install -e ".[parquet]"
laps.save("exports/brazil_2025_44.parquet")

# Optional: pip install -e ".[pandas]"
dataframe = laps.to_pandas()
~~~

Each Dataset holds records, source, url, fetched_at, cached and metadata, as well as Python iteration and indexing.

### Optional FastF1 bridge

~~~bash
python -m pip install -e ".[fastf1]"
~~~

~~~python
from apexium.fastf1_bridge import load_session

session = load_session(2025, "Brazil", "R")
print(session.laps.head())
~~~

This bridge returns a genuine FastF1 Session without copying or pretending to replace FastF1's advanced functionality.

---

## How the platform works

~~~text
Developers, researchers, bots, apps and dashboards
                |
      +---------+----------+
      |                    |
 Python SDK & CLI      JavaScript SDK
      |                    |
 SQLite TTL cache     In-memory TTL cache
      |                    |
      +---------+----------+
                |
        HTTP with retries
                |
        +-------+--------+
        |                |
      OpenF1           Jolpica
   2023+ details     1950+ history

Optional Python bridge -> FastF1
~~~

The two SDKs have intentionally small dependency surfaces. Rust/WASM, SQL analytics, plotting components, distributed data storage and live-event subscriptions are **future milestones**, not existing features.

## Data access, accuracy and legal boundaries

APEXIUM is **not affiliated with Formula 1, the FIA, OpenF1, FastF1, or Jolpica**.

- **OpenF1:** Historical telemetry and session data are publicly accessible from 2023 onward. Live data is subscription-restricted. Documentation: https://openf1.org/docs/
- **Jolpica:** Historical championship information from 1950 onward, subject to API throttling and usage conditions. Documentation: https://api.jolpi.ca/docs/ and https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md
- **FastF1:** Optional integration using FastF1's own Python package. Documentation: https://docs.fastf1.dev/

APEXIUM does not bypass authentication, access controls or provider rate limits. Source terms and redistribution permissions apply separately from APEXIUM's MIT-licensed source code. Public API data may be corrected, delayed, incomplete or unavailable.

Cache defaults: Python disk cache 6 hours for most API calls / 10 seconds for OpenF1 queries with “latest”; JavaScript memory cache uses the same durations. Call the provider query with ttl=0 in Python, or {ttl: 0} in JavaScript, to disable caching on that request. Sustained provider quotas are not globally enforced across separate processes.

## Quality gates

~~~bash
# Python: offline tests, no API keys or live calls
python -m unittest discover -s tests -v
python -m compileall -q apexium

# JavaScript: offline Node built-in test runner
cd sdk/javascript
npm test
~~~

CI executes Python tests on Python 3.10–3.13 and JavaScript tests on Node 20/22.

**We do not publish fabricated benchmarks.** Performance and stability claims will be added only with a public benchmark script, repeatable dataset, hardware information, baseline and CI evidence. See [benchmark methodology](docs/benchmarks.md).

## Development principles

1. Correctness over inflated counts or decorative APIs.
2. One well-tested implementation for every advertised feature.
3. No required keys for publicly available historical endpoints.
4. Source provenance and explicit errors, not silent invented values.
5. Stable and documented public interfaces with semantic versioning.
6. Offline fixtures and source-specific contract tests.
7. Accessible documentation, minimal setup and welcoming contribution guidelines.

## Roadmap

- **1.0.0 source / alpha:** Python + JavaScript providers, local cache, export, CLI, analytics, offline tests.
- **Next:** upstream live smoke tests, stronger runtime typing, API compatibility contracts, CORS guidance, full TypeScript definitions.
- **Later:** streaming adapters only where legally accessible; richer visualizations and circuit geometry; WebAssembly after benchmarks justify it; reproducible analytical research modules.

Detailed plan: [docs/roadmap.md](docs/roadmap.md).

## Contributing and security

Issues and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Do not submit private API credentials, unauthorized data dumps, or copyrighted media.

## License

MIT for APEXIUM's own source code; upstream datasets and third-party marks retain their respective rights. See [LICENSE](LICENSE).

---

**APEXIUM — build once, analyze with evidence, share with everyone.**
