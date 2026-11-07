# Architecture and engineering rationale

## Scope

APEXIUM acts as an **adapter and analysis layer**, not a data host. External data stays authoritative. APEXIUM does not redistribute a master copy of a third-party dataset.

### Python modules

- apexium.client: public Apexium facade, lazy Race meeting/session selector.
- apexium.openf1: explicit 18-endpoint routing, query validation and operators.
- apexium.jolpica: historical API routing and pagination.
- apexium.transport: shared HTTP error policy, min-interval pacing and SQLite TTL cache.
- apexium.dataset: data provenance and common exports.
- apexium.analytics and analytics_extra: 20 deterministic descriptive calculations.
- apexium.fastf1_bridge: opt-in FastF1 integration.
- apexium.cli: command line entry point.

### JavaScript modules

- sdk/javascript/index.js: native fetch, ESM, response metadata and in-memory caching.
- sdk/javascript/index.d.ts: baseline static declarations.
- sdk/javascript/test.js: Node built-in offline test fixtures.

## Consistency contract

Providers retain their own field names and structures. The unified aspect of APEXIUM is:
- one client object with named providers;
- the same predictable metadata envelope;
- common session selection and exception semantics;
- explicit rather than silently distorted data.

Jolpica races are nested; OpenF1 responses are row-oriented. They are not coerced into a misleading pretend-global schema.

## Operational requirements

- Avoid fetching entire multi-driver high-frequency telemetry without filters.
- Respect each source's rate limits, authentication, commercial-use terms and availability.
- Do not infer that cache equals permanently authoritative data.
- Prefer source-specific unit tests, offline fixtures and periodically scheduled live contract tests with explicit network permission.
- Do not store credentials in git, logs or exported datasets.
- Note that SQLite and in-memory cache are per-process/per-device; neither enforces a global quota.

## Why no forced Rust, WASM or ML in the initial source?

Performance engineering requires profiling. A correct lightweight Python/JS client can be faster to adopt than a cross-compiled platform that adds installation cost. Rust, Arrow or WASM should only enter when public benchmarks prove a meaningful advantage. ML should never hide unknown input data or invent a missing result.

## Data-flow

~~~text
User code -> Python/JS facade -> route validation -> source adapter
                                     |
                         cache lookup / retry / throttle
                                     |
                                upstream API
                                     |
                     source-shaped rows + metadata
                                     |
                analysis / JSON / CSV / optional Parquet
~~~

## Security

Only known resource identifiers are accepted. Jolpica path segments and OpenF1 filter names are validated. Requests use HTTPS default endpoints. Timeouts and transient retry bounds are finite. Custom bases are developer options, not arbitrary user-controlled URL proxies.
