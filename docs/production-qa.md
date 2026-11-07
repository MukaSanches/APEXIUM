# Production QA — APEXIUM Studio

Homepage data must **work in the actual browser**, not merely be available via JSON.

## The 2026-11-07 defect

The Jolpica API from a browser may be restricted by CORS/User-Agent conditions.
The first fix deployed same-origin JSON snapshots, but previous PWA installations
could retain old JavaScript and the continuous integration only tested raw JSON URLs
and local fixtures. Browser screenshots still showed empty standings and calendar.

## New defense-in-depth

1. On every publish, GitHub Actions requests real Jolpica data with an identifiable
   User-Agent; the source is preserved in each snapshot, with license attribution.
2. A real snapshot bundle is **embedded directly in the released index.html**.
   The initial homepage no longer needs a network fetch to paint standings/calendar.
3. Scripts and CSS carry an asset revision query to evade stale Service Worker caches.
4. Service worker cache namespace increments, removing previous app-shell caches.
5. Both the static assets and the actual published DOM are verified after deploy.
6. An **unmocked Playwright browser test** checks 2026 metrics and standings,
   2026 calendar, 2025 calendar, and reload behavior. Failures upload a screenshot.

The OpenF1 telemetry/API remains a separate source with its own access limitations.

## Interpretation

A green workflow is required, not sufficient evidence for every operating system
and browser extension combination. The unmocked Chromium production test verifies
real published data; independent Opera GX checks remain advisable.

## Running locally

For a published site:
~~~bash
python -m pip install playwright
python -m playwright install chromium --only-shell
python tests/live_site_smoke.py
~~~

For the public deployment, review the **Verify the actual public site** workflow
step and its browser screenshot artifact.
