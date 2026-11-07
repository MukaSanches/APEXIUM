"""Live, unmocked production verification of the user-facing GitHub Pages UI.

Run on GitHub Actions after deploy. This tests real DOM + real published data,
not fixtures or only static HTTP availability. Screenshots on failure.
"""
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

SITE = os.getenv("APEXIUM_SITE_URL", "https://mukasanches.github.io/APEXIUM/")
TARGET = urljoin(SITE.rstrip("/") + "/", "?release=20261107c#overview")
OUTPUT = Path("apexium-production-desktop.png")


def main():
    diagnostics = []
    with sync_playwright() as runner:
        browser = runner.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900},
                                      service_workers="allow")
        page = context.new_page()
        page.on("pageerror", lambda error: diagnostics.append("PAGE ERROR: " + str(error)))
        page.on("requestfailed", lambda req:
                diagnostics.append("REQUEST FAILED: " + req.url + " " +
                                   str(req.failure)))
        page.on("console", lambda msg: diagnostics.append(
            "CONSOLE: " + msg.type + " " + msg.text
        ) if msg.type == "error" else None)
        try:
            response = page.goto(TARGET, wait_until="domcontentloaded",
                                 timeout=60000)
            assert response and response.status == 200, "Landing page not HTTP 200"
            page.wait_for_function("""() => {
              const races = Number(document.querySelector('#metric-races')?.textContent);
              const drivers = Number(document.querySelector('#metric-drivers')?.textContent);
              const leader = document.querySelector('#metric-leader')?.textContent?.trim();
              const entries = document.querySelectorAll('#overview-standing .ranking-row').length;
              return races >= 15 && drivers >= 10 && leader && leader !== '—' && entries >= 5;
            }""", timeout=30000)
            count = page.locator("#metric-races").inner_text()
            names = page.locator("#overview-standing .ranking-row").count()
            assert int(count) >= 15 and names >= 5
            assert "Não foi possível carregar" not in page.locator("#overview-standing").inner_text()
            assert "Não foi possível carregar" not in page.locator("#overview-events").inner_text()
            assert page.locator("#feed-freshness").inner_text().strip()
            print("Production 2026 overview OK:", count, "races,", names, "drivers")

            page.locator('.sidebar [data-nav="championship"]').click()
            page.wait_for_function(
              "() => document.querySelectorAll('#full-standings .standing-full-row').length>=10",
              timeout=25000)
            print("Production championship OK")
            page.locator('.sidebar [data-nav="calendar"]').click()
            page.wait_for_function(
              "() => document.querySelectorAll('#calendar-events .calendar-card').length>=15",
              timeout=25000)
            print("Production calendar OK")

            page.locator("#season-select").select_option("2025")
            page.wait_for_function(
              "() => document.querySelectorAll('#calendar-events .calendar-card').length>=20",
              timeout=25000)
            print("Production historic 2025 calendar OK")

            page.locator("#season-select").select_option("2026")
            page.locator('.sidebar [data-nav="overview"]').click()
            page.wait_for_function(
              "() => Number(document.querySelector('#metric-races')?.textContent)>=15",
              timeout=30000)

            # Unmocked Lab: 2026 completed historical race and real timed laps.
            page.locator('.sidebar [data-nav="lab"]').click()
            page.wait_for_function(
                "() => document.querySelectorAll('#lab-race option').length >= 2",
                timeout=30000)
            page.wait_for_function(
                "() => [...document.querySelectorAll('#lab-driver-a option')].some(o => o.textContent.includes('#'))",
                timeout=25000)
            page.locator("#lab-analysis").select_option("racePace")
            page.locator("#run-analysis").click()
            page.wait_for_function(
                "() => document.querySelectorAll('#lab-result .data-table tbody tr').length>=5",
                timeout=30000)
            assert "Não foi possível carregar" not in page.locator("#lab-result").inner_text()
            print("Production Race Lab OK:",page.locator("#lab-race").input_value())

            # Unmocked three additional analysis families: tyre strategy,
            # weather and sampled car telemetrics (the latter is intentionally bounded).
            page.locator("#lab-analysis").select_option("stintStrategies")
            page.locator("#run-analysis").click()
            page.wait_for_function(
                "() => document.querySelectorAll('#lab-result .data-table tbody tr').length>=5",
                timeout=25000)
            page.locator("#lab-analysis").select_option("weatherSummary")
            page.locator("#run-analysis").click()
            page.wait_for_function(
                "() => document.querySelector('#lab-result .data-table tbody tr')!==null",
                timeout=25000)

            page.locator('.sidebar [data-nav="telemetry"]').click()
            page.wait_for_function(
                "() => document.querySelectorAll('#telemetry-race option').length>=2",
                timeout=30000)
            page.locator("#telemetry-race").select_option(index=1)
            page.wait_for_function(
                "() => !!document.querySelector('#telemetry-driver option[value]:not([value=\"\"])')",
                timeout=30000)
            page.wait_for_function(
                "() => !!document.querySelector('#telemetry-lap option[value]:not([value=\"\"])')",
                timeout=30000)
            page.locator("#run-telemetry").click()
            page.wait_for_function(
                "() => document.querySelectorAll('#telemetry-chart .signal-chart').length===4",
                timeout=30000)
            assert int(page.locator("#telemetry-samples").inner_text().replace(".",""))>=20
            print("Production telemetry OK:",
                  page.locator("#telemetry-samples").inner_text(),"real samples")

            page.locator('.sidebar [data-nav="explorer"]').click()
            page.locator("#explorer-provider").select_option("openf1")
            page.locator("#explorer-resource").select_option("meetings")
            page.locator("#run-explorer").click()
            page.wait_for_function(
                "() => document.querySelector('#explorer-results .data-table tbody tr')!==null",
                timeout=30000)
            page.locator("#explorer-resource").select_option("laps")
            page.wait_for_function(
                "() => document.querySelector('#explorer-session').value.includes('session_key=')",
                timeout=20000)
            page.locator("#run-explorer").click()
            page.wait_for_function(
                "() => document.querySelectorAll('#explorer-results .data-table tbody tr').length>=10",
                timeout=30000)
            page.locator("#explorer-provider").select_option("jolpica")
            page.locator("#explorer-resource").select_option("races")
            page.locator("#run-explorer").click()
            page.wait_for_function(
                "() => document.querySelectorAll('#explorer-results .data-table tbody tr').length>=10",
                timeout=30000)
            print("Production Data Explorer OK: OpenF1 and Jolpica")

            # Repeat with a service worker registered, as in a real installed PWA.
            page.reload(wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function(
              "() => Number(document.querySelector('#metric-races')?.textContent)>=15",
              timeout=30000)
            print("Production service-worker/reload OK")

            page.screenshot(path=str(OUTPUT), full_page=True)
            print("UNMOCKED PRODUCTION BROWSER TESTS PASSED")
            return 0
        except Exception as exc:
            print("UNMOCKED PRODUCTION BROWSER TESTS FAILED:", repr(exc), file=sys.stderr)
            print("CURRENT URL:", page.url, file=sys.stderr)
            print("METRIC RACES:", page.locator("#metric-races").inner_text()
                  if page.locator("#metric-races").count() else "<missing>", file=sys.stderr)
            print("STANDING BODY:", page.locator("#overview-standing").inner_text()[:500]
                  if page.locator("#overview-standing").count() else "<missing>", file=sys.stderr)
            for item in diagnostics[-25:]:
                print(item, file=sys.stderr)
            page.screenshot(path=str(OUTPUT), full_page=True)
            return 1
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
