"""All offline: predictable test fixtures, no third-party API requests."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from apexium import analytics
from apexium.client import Race
from apexium.dataset import Dataset
from apexium.jolpica import Jolpica
from apexium.openf1 import ENDPOINTS, OpenF1
from apexium.transport import APIError, SQLiteCache, Transport


class Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.value).encode()


class FakeOpen:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, request, timeout=0):
        self.calls.append(request.full_url)
        return Response(self.payload)


class TransportTests(unittest.TestCase):
    def test_cache_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = FakeOpen([{"driver_number": 44}])
            cache = SQLiteCache(Path(directory) / "test.sqlite")
            http = Transport(opener=fake, cache=cache, min_interval=0)
            one = http.get("https://example.com/a", source="openf1")
            two = http.get("https://example.com/a", source="openf1")
            self.assertEqual(len(fake.calls), 1)
            self.assertFalse(one.cached)
            self.assertTrue(two.cached)
            self.assertEqual(two.records, one.records)
            cache.clear()
            http.get("https://example.com/a", source="openf1")
            self.assertEqual(len(fake.calls), 2)

    def test_http_error(self):
        def fail(*args, **kwargs):
            raise HTTPError("https://example.com", 404, "not found",
                            {}, io.BytesIO(b"missing"))
        with self.assertRaises(APIError) as context:
            Transport(opener=fail, retries=0, min_interval=0).get(
                "https://example.com", source="openf1"
            )
        self.assertEqual(context.exception.status, 404)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            Transport(timeout=0)

    def test_invalid_shape(self):
        http = Transport(opener=FakeOpen({}), retries=0, min_interval=0)
        with self.assertRaises(RuntimeError):
            http.get("https://example.com", source="openf1", ttl=0)


class ProvidersTests(unittest.TestCase):
    def test_openf1_all_endpoints(self):
        self.assertEqual(len(ENDPOINTS), 18)
        api = OpenF1(Transport(opener=FakeOpen([]), min_interval=0))
        for method in ENDPOINTS:
            self.assertEqual(getattr(api, method)(session_key=9165).records, [])

    def test_openf1_encoded_comparators(self):
        fake = FakeOpen([])
        api = OpenF1(Transport(opener=fake, min_interval=0))
        api.laps(driver_number=44, lap_duration__gte=90, is_pit_out_lap=False)
        query = parse_qs(urlparse(fake.calls[0]).query)
        self.assertEqual(query["lap_duration>"], ["90"])
        self.assertEqual(query["is_pit_out_lap"], ["false"])

    def test_openf1_validates(self):
        api = OpenF1(Transport(opener=FakeOpen([]), min_interval=0))
        with self.assertRaises(ValueError):
            api.query("not_real")
        with self.assertRaises(ValueError):
            api.query("laps", **{"hello;evil": "x"})

    def test_jolpica_results_and_metadata(self):
        payload = {"MRData": {"total": "1", "limit": "100", "RaceTable": {
            "Races": [{"round": "1", "Results": [{"position": "1"}]}]}}}
        fake = FakeOpen(payload)
        api = Jolpica(Transport(opener=fake, min_interval=0))
        result = api.results(2025, 1)
        self.assertEqual(result.records[0]["round"], "1")
        self.assertEqual(result.metadata["total"], "1")
        self.assertIn("/2025/1/results.json", fake.calls[0])

    def test_jolpica_standings(self):
        payload = {"MRData": {"StandingsTable": {"StandingsLists": [
            {"DriverStandings": [{"points": "100"}]}]}}}
        api = Jolpica(Transport(opener=FakeOpen(payload), min_interval=0))
        self.assertEqual(api.driver_standings(2025).records[0]
                         ["DriverStandings"][0]["points"], "100")

    def test_reject_injection(self):
        api = Jolpica(Transport(opener=FakeOpen({}), min_interval=0))
        with self.assertRaises(ValueError):
            api.results("../secret")
        with self.assertRaises(ValueError):
            api.query("results", limit=0)
        with self.assertRaises(ValueError):
            api.query("bad_resource")

    def test_all_pages(self):
        def make_page(req, timeout=0):
            offset = int(parse_qs(urlparse(req.full_url).query)["offset"][0])
            return Response({"MRData": {"total": "3", "RaceTable": {
                "Races": [{"round": str(i)} for i in range(offset, min(3, offset+2))]}}})
        api = Jolpica(Transport(opener=make_page, min_interval=0))
        result = api.all_pages("races", page_size=2, max_pages=3)
        self.assertEqual(len(result), 3)


class RaceTests(unittest.TestCase):
    def setUp(self):
        self.api = OpenF1(Transport(opener=FakeOpen([]), min_interval=0))
        self.race = Race(self.api, 2025, "Brazil")

    def test_select_meeting_and_race(self):
        def meetings(**filters):
            return Dataset([{"meeting_key": 1, "country_name": "Brazil",
                             "meeting_name": "São Paulo Grand Prix"}],
                           "openf1", "example", "now")
        def sessions(**filters):
            return Dataset([{"session_key": 2, "session_name": "Sprint", "session_type": "Race"},
                            {"session_key": 3, "session_name": "Race", "session_type": "Race"}],
                           "openf1", "example", "now")
        self.api.meetings = meetings
        self.api.sessions = sessions
        self.assertEqual(self.race.meeting_key, 1)
        self.assertEqual(self.race.session_key, 3)

    def test_ambiguous_meeting(self):
        self.api.meetings = lambda **_: Dataset([
            {"meeting_key": 1, "country_name": "Brazil"},
            {"meeting_key": 2, "country_name": "Brazil"},
        ], "openf1", "x", "now")
        with self.assertRaises(RuntimeError):
            _ = self.race.meeting

    def test_no_race(self):
        self.api.meetings = lambda **_: Dataset([{
            "meeting_key": 1, "country_name": "Brazil"}],
            "openf1", "x", "now")
        self.api.sessions = lambda **_: Dataset([], "openf1", "x", "now")
        with self.assertRaises(RuntimeError):
            _ = self.race.session


class DatasetTests(unittest.TestCase):
    def test_export(self):
        ds = Dataset([{"name": "São Paulo", "nested": [1, 2]}],
                     "openf1", "url", "now")
        self.assertIn("São Paulo", ds.to_json())
        with tempfile.TemporaryDirectory() as directory:
            csv = ds.save(Path(directory) / "dataset.csv")
            jsn = ds.save(Path(directory) / "dataset.json")
            self.assertIn("nested", csv.read_text())
            self.assertEqual(json.loads(jsn.read_text()), ds.records)
            with self.assertRaises(ValueError):
                ds.save(Path(directory) / "bad.txt")

    def test_empty_csv(self):
        self.assertEqual(Dataset([], "x", "y", "now").to_csv(), "")


class AnalyticsTests(unittest.TestCase):
    def test_race_pace(self):
        data = [{"driver_number": 44, "lap_duration": t} for t in [90, 91, 92]]
        data += [{"driver_number": 1, "lap_duration": t} for t in [88, 90, 91]]
        data += [{"driver_number": 3, "lap_duration": 89, "is_pit_out_lap": True}]
        result = analytics.race_pace(data)
        self.assertEqual(result[0]["driver_number"], 1)
        self.assertEqual(result[0]["median_seconds"], 90.0)

    def test_invalid_race_pace(self):
        with self.assertRaises(ValueError):
            analytics.race_pace([], min_laps=0)

    def test_pits(self):
        result = analytics.pit_summary([
            {"driver_number": 4, "lane_duration": 22.4, "stop_duration": None},
            {"driver_number": 4, "lane_duration": 23.0, "stop_duration": 2.1},
        ])[0]
        self.assertEqual(result["pit_entries"], 2)
        self.assertEqual(result["measured_stationary_stops"], 1)

    def test_positions(self):
        result = analytics.position_changes([
            {"driver_number": 3, "date": "2024-01-01T00:00:02", "position": 2},
            {"driver_number": 3, "date": "2024-01-01T00:00:01", "position": 5},
        ])
        self.assertEqual(result[0]["net_gain"], 3)

    def test_stints_and_swaps(self):
        self.assertEqual(analytics.stint_summary([
            {"driver_number": 1, "lap_start": 1, "lap_end": 20}
        ])[0]["laps"], 20)
        self.assertEqual(analytics.overtaking_counts([
            {"overtaking_driver_number": 44}, {"overtaking_driver_number": 44}
        ])[0]["recorded_position_swaps"], 2)

    def test_quality(self):
        report = analytics.lap_quality([
            {"driver_number": 1, "lap_number": 1, "session_key": 5,
             "lap_duration": 90.0},
            {"driver_number": 1, "lap_number": 1, "session_key": 5,
             "lap_duration": -1.0},
        ])
        self.assertEqual(report["duplicate_driver_lap_session"], 1)
        self.assertEqual(report["invalid_lap_duration"], 1)


if __name__ == "__main__":
    unittest.main()
