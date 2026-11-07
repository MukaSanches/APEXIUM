# Benchmark methodology

APEXIUM does **not** report unverified speedups over FastF1, OpenF1 clients or other libraries.

## What would justify a claim?

Measure the same dataset, source, environment and cache state. Publish:
- API and library version/commit.
- Hardware and operating system.
- Python/Node version and optional dependencies.
- Data size, query, filters and whether results include full telemetry.
- Cold and warm cache latency separately.
- Throughput, memory peak and failure rate, with repeated samples.
- Competitors' documented settings and version.
- Raw measurement files and replay script.

For network-bound queries, the provider and rate limit dominate throughput. A client cannot ethically improve provider throughput by bypassing quotas.

## Adoption metrics

GitHub stars, PyPI or npm download events, distinct projects, dependents, retention and issue-response time each measure different things. Do not equate downloads with distinct users. A record requires an explicitly chosen comparison set, measurement window and source.
