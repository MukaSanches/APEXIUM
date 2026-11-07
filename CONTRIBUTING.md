# Contributing to APEXIUM

Thanks for contributing to an evidence-first, accessible Formula 1 toolkit.

1. Open an issue describing the problem and the expected data source.
2. Fork the repository and create a focused branch.
3. Add offline deterministic tests for all behavior changes.
4. Preserve original data semantics; do not fabricate fields or measurements.
5. Avoid heavy required runtime dependencies; optional additions need rationale.
6. Run the tests described below before opening a pull request.
7. Describe API compatibility, provider terms and backwards compatibility.

~~~bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q apexium
cd sdk/javascript && npm test
~~~

For new provider endpoints, include an upstream documentation link, supported filters, sample payload shape and whether access is free, authenticated or restricted.

No credentials, copyrighted broadcast clips, private datasets or copyrighted logos in contributions. Keep discussions respectful and technical.

Maintainers review PRs as time allows; no review SLA is promised.
