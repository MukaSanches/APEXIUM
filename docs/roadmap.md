# Development roadmap

## Source 1.0.0 (alpha): present in this repository

- Python: OpenF1 adapter (18 routes), Jolpica adapter (13 resources), source-aware datasets, HTTP retries, disk cache, exports, high-level race facade, twenty descriptive analytics, CLI, optional FastF1 bridge.
- JavaScript: Node/browser-compatible ESM adapter to both APIs, in-memory cache, high-level race context and two analyses.
- Offline tests on both runtimes and continuous integration configuration.
- Documentation, contribution guide and security reporting procedure.

## Milestone A — external validation

- Live OpenF1/Jolpica smoke tests using small safe public sample requests.
- Schema/contract checks across past seasons and weekends.
- Independent review of accuracy and data licenses.
- Fix API compatibility discovered in real-world usage.
- Publish a release only after evidence supports its stability.

## Milestone B — adoption

- Full TypeScript surface typing.
- Release packages on package registries after checking namespace availability.
- End-to-end user guides and examples for popular frontend frameworks.
- Benchmarks, code coverage reporting, compatibility matrix and release automation.
- Improve persistent caching and page streaming under quota constraints.

## Milestone C — optional expansion

- Polars/Arrow and DuckDB adapters for large offline analytics.
- Interactive circuit map and charts as separate packages.
- Authorized event stream plugins (no bypass of live data subscriptions).
- Open data validation and anomaly detection with rigorous uncertainty reporting.
- Rust/WASM for proven compute bottlenecks only.

Record-breaking adoption is a goal to investigate, not an existing fact.
