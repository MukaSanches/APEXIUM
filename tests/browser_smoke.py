"""Browser journey tests for nontechnical users. All third-party APIs are mocked.

This is an offline UI integration test: real upstream availability, coverage and
permission constraints still require separate smoke tests.
"""
import json
import os
import mimetypes
import subprocess
import time
import unittest
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:4173"

DRIVERS = [
    {"driver_number":44,"full_name":"Dora Vale","name_acronym":"DVA"},
    {"driver_number":1,"full_name":"Max Silva","name_acronym":"MSI"},
]
MEETINGS = [{"meeting_key":600,"meeting_name":"São Paulo Grand Prix","country_name":"Brazil", "location":"São Paulo", "date_start":"2026-10-30T12:00:00Z"}]
SESSIONS = [{"meeting_key":600,"session_key":333,"session_name":"Sprint","session_type":"Race"},{"meeting_key":600,"session_key":334,"session_name":"Race","session_type":"Race"}]
LAPS = [
    {"session_key":334,"driver_number":driver,"lap_number":i,"lap_duration":90.0+i*.2+(driver==44),"date_start":f"2026-10-31T15:{i:02}:00+00:00","duration_sector_1":30,"duration_sector_2":31,"duration_sector_3":30}
    for driver in (44,1) for i in (1,2,3,4)
]
CAR_DATA = [{"session_key":334,"driver_number":44,"speed":speed,"throttle":throttle,"brake":brake,"rpm":rpm,"date":"2026-10-31T15:01:01Z"} for speed,throttle,brake,rpm in [(180,100,0,8000),(240,100,0,9200),(110,0,100,6500)]]
RACES = [
    {"season":"2026","round":"1","raceName":"Grand Prix de Teste 1","date":"2026-05-01","time":"12:00:00Z","Circuit":{"circuitName":"Test Circuit","Location":{"country":"Brazil"}}},
    {"season":"2026","round":"2","raceName":"Grand Prix de Teste 2","date":"2026-12-01","time":"12:00:00Z","Circuit":{"circuitName":"Test Circuit 2","Location":{"country":"Japan"}}},
]
DRIVER_STANDINGS=[{"position":"1","points":"100","wins":"2","Driver":{"givenName":"Dora","familyName":"Vale","code":"DVA"},"Constructors":[{"name":"Team A"}]},{"position":"2","points":"70","wins":"1","Driver":{"givenName":"Max","familyName":"Silva","code":"MSI"},"Constructors":[{"name":"Team B"}]}]
CONSTRUCTOR_STANDINGS=[{"position":"1","points":"130","wins":"3","Constructor":{"name":"Team A"}},{"position":"2","points":"90","wins":"1","Constructor":{"name":"Team B"}}]


def handler(route):
    url = route.request.url
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path
    if parsed.hostname == 'api.jolpi.ca':
        if path.endswith('/races.json'):
            payload = {"MRData":{"total":"2","RaceTable":{"Races":RACES}}}
        elif path.endswith('/driverstandings.json'):
            payload = {"MRData":{"total":"1","StandingsTable":{"StandingsLists":[{"DriverStandings":DRIVER_STANDINGS}]}}}
        elif path.endswith('/constructorstandings.json'):
            payload = {"MRData":{"total":"1","StandingsTable":{"StandingsLists":[{"ConstructorStandings":CONSTRUCTOR_STANDINGS}]}}}
        else:
            payload = {"MRData":{"total":"0","RaceTable":{"Races":[]}}}
    elif parsed.hostname == 'api.openf1.org':
        resource = path.rsplit('/',1)[-1]
        payload = {
            'meetings':MEETINGS,'sessions':SESSIONS,'drivers':DRIVERS,'laps':LAPS,
            'car_data':CAR_DATA,'stints':[{'driver_number':44,'lap_start':1,'lap_end':4,'compound':'SOFT'}],
            'pit':[{'driver_number':44,'lap_number':2,'lane_duration':25,'stop_duration':2.5}],
            'position':[{'driver_number':44,'date':'2026-10-31T15:00:00Z','position':3}],
            'weather':[{'track_temperature':28,'air_temperature':21,'rainfall':0}],
            'race_control':[{'category':'Flag','flag':'GREEN'}],
            'session_result':[{'driver_number':44,'position':1}],
        }.get(resource,[])
    else:
        route.abort()
        return
    route.fulfill(status=200,content_type='application/json',body=json.dumps(payload),headers={'Access-Control-Allow-Origin':'*'})


def browser_provider_fetch_mock():
    """Mock the browser fetch boundary, preserving the real API response shapes.

    This avoids dependence on CORS/preflight variations in Chromium runners while
    exercising the complete production JavaScript UI and calculation logic.
    """
    openf1 = {
        'meetings': MEETINGS, 'sessions': SESSIONS, 'drivers': DRIVERS,
        'laps': LAPS, 'car_data': CAR_DATA,
        'stints': [{'driver_number':44,'lap_start':1,'lap_end':4,'compound':'SOFT'}],
        'pit': [{'driver_number':44,'lap_number':2,'lane_duration':25,'stop_duration':2.5}],
        'position': [{'driver_number':44,'date':'2026-10-31T15:00:00Z','position':3}],
        'weather': [{'track_temperature':28,'air_temperature':21,'rainfall':0}],
        'race_control': [{'category':'Flag','flag':'GREEN'}],
        'session_result': [{'driver_number':44,'position':1}],
    }
    jolpica = {
        'races': {'MRData':{'total':'2','RaceTable':{'Races':RACES}}},
        'driverstandings': {'MRData':{'total':'1','StandingsTable':{
            'StandingsLists':[{'DriverStandings':DRIVER_STANDINGS}]}}},
        'constructorstandings': {'MRData':{'total':'1','StandingsTable':{
            'StandingsLists':[{'ConstructorStandings':CONSTRUCTOR_STANDINGS}]}}},
    }
    return """(() => {
      const realFetch = window.fetch.bind(window);
      const openf1 = %s;
      const jolpica = %s;
      window.fetch = (input, options) => {
        const url = new URL(input?.url ?? String(input), location.href);
        let data;
        if (url.hostname === 'api.openf1.org') {
          data = openf1[url.pathname.split('/').pop()] ?? [];
          if (url.searchParams.has('driver_number')) {
            const selected = Number(url.searchParams.get('driver_number'));
            data = data.filter(row => Number(row.driver_number) === selected);
          }
        } else if (url.hostname === 'api.jolpi.ca') {
          data = jolpica[url.pathname.split('/').pop().replace(/\\.json$/, '')] ??
            {MRData:{total:'0',RaceTable:{Races:[]}}};
        } else return realFetch(input, options);
        return Promise.resolve(new Response(JSON.stringify(data), {
          status: 200, headers: {'Content-Type': 'application/json'}
        }));
      };
    })();""" % (json.dumps(openf1), json.dumps(jolpica))


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['node','scripts/build-site.mjs'],cwd=ROOT,check=True)
        cls.server=subprocess.Popen(['node','scripts/serve-site.mjs'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(40):
            try:
                with urlopen(BASE,timeout=1) as response:
                    if response.status==200:break
            except Exception:
                time.sleep(.25)
        else:
            cls.server.terminate()
            raise RuntimeError('Static preview did not start')
        cls.play=sync_playwright().start()
        cls.browser=cls.play.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_PATH') or None,args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.play.stop()
        cls.server.terminate()
        cls.server.wait(timeout=8)

    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':980},service_workers='block',accept_downloads=True)
        self.context.add_init_script(script=browser_provider_fetch_mock())
        self.page=self.context.new_page()
        self.errors=[]
        self.page.on('pageerror',lambda exc:self.errors.append(str(exc)))
        self.messages=[]
        self.page.on('console',lambda msg:self.messages.append(f"console {msg.type}: {msg.text}"))
        self.page.on('requestfailed',lambda req:self.messages.append(f"request failed: {req.url}: {req.failure}"))
        self.page.goto(BASE,wait_until='domcontentloaded')
        self.page.wait_for_timeout(350)
        if self.page.locator('#lab-analysis option').count() < 15:
            print('APEXIUM BROWSER DIAGNOSTIC:', self.messages[:20],
                  'script tags:', self.page.locator('script').count(), flush=True)

    def tearDown(self):
        self.assertEqual(self.errors,[],f'Browser JavaScript errors: {self.errors}')
        self.context.close()

    def test_overview_and_championship(self):
        expect(self.page.locator('#metric-races')).to_have_text('2',timeout=15000)
        expect(self.page.locator('#metric-leader')).to_have_text('Dora Vale')
        self.page.locator('.sidebar [data-nav="championship"]').click()
        expect(self.page.locator('#full-standings')).to_contain_text('Dora Vale')
        self.page.locator('[data-standing="constructors"]').click()
        expect(self.page.locator('#full-standings')).to_contain_text('Team A')

    def test_calendar_search(self):
        self.page.locator('.sidebar [data-nav="calendar"]').click()
        expect(self.page.locator('.calendar-card')).to_have_count(2)
        self.page.locator('#calendar-search').fill('Teste 2')
        expect(self.page.locator('.calendar-card')).to_have_count(1)

    def test_lab_with_real_shape_mock_records(self):
        self.page.locator('.sidebar [data-nav="lab"]').click()
        expect(self.page.locator('#lab-race option')).to_have_count(2)
        self.page.locator('#lab-race').select_option('600')
        self.page.locator('#run-analysis').click()
        expect(self.page.locator('#lab-result')).to_contain_text('median seconds')
        expect(self.page.locator('#lab-result')).to_contain_text('44')
        expect(self.page.locator('#export-analysis')).to_be_enabled()
        self.page.locator('#lab-analysis').select_option('lapDeltas')
        self.page.locator('#lab-driver-a').select_option('44')
        self.page.locator('#lab-driver-b').select_option('1')
        self.page.locator('#run-analysis').click()
        expect(self.page.locator('#lab-result')).to_contain_text('delta a minus b seconds')

    def test_telemetry_graphs_and_pwa(self):
        self.page.locator('.sidebar [data-nav="telemetry"]').click()
        expect(self.page.locator('#telemetry-race option')).to_have_count(2)
        self.page.locator('#telemetry-race').select_option('600')
        self.page.locator('#telemetry-driver').select_option('44')
        expect(self.page.locator('#telemetry-lap option')).to_have_count(4)
        self.page.locator('#run-telemetry').click()
        expect(self.page.locator('#telemetry-max-speed')).to_have_text('240')
        expect(self.page.locator('#telemetry-chart .signal-chart')).to_have_count(4)
        manifest=self.page.request.get(BASE+'/manifest.webmanifest')
        self.assertEqual(manifest.status,200)
        self.assertEqual(manifest.json()['display'],'standalone')

    def test_explorer_export_and_mobile_navigation(self):
        self.page.locator('.sidebar [data-nav="explorer"]').click()
        self.page.locator('#explorer-resource').select_option('meetings')
        self.page.locator('#run-explorer').click()
        expect(self.page.locator('#explorer-results')).to_contain_text('São Paulo')
        with self.page.expect_download() as info:
            self.page.locator('#export-json').click()
        self.assertTrue(info.value.suggested_filename.endswith('.json'))
        self.page.set_viewport_size({'width':390,'height':844})
        expect(self.page.locator('.mobile-nav')).to_be_visible()
        self.page.locator('.mobile-nav [data-nav="overview"]').click()
        expect(self.page.locator('#view-overview')).to_be_visible()
        self.page.screenshot(path=str(ROOT/'mobile-smoke.png'),full_page=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
