"""Additional pure-analysis regression tests; no network involved."""
import unittest

from apexium.analytics_extra import (
    fastest_laps, ideal_laps, sector_pace, lap_trends, compound_pace,
    stint_strategies, pit_window_histogram, speed_summary, throttle_brake_summary,
    drs_code_summary, weather_summary, race_control_summary, lap_deltas,
    position_trajectory,
)


class ExtraAnalyticsTests(unittest.TestCase):
    def test_fastest(self):
        result = fastest_laps([{"driver_number": 1, "lap_number": 4, "lap_duration": 92},
                               {"driver_number": 1, "lap_number": 5, "lap_duration": 90}])
        self.assertEqual(result[0]["lap_number"], 5)

    def test_ideal(self):
        sample = [
            {"driver_number": 1, "duration_sector_1": 30,
             "duration_sector_2": 31, "duration_sector_3": 32, "lap_duration": 93},
            {"driver_number": 1, "duration_sector_1": 28,
             "duration_sector_2": 32, "duration_sector_3": 30, "lap_duration": 90},
        ]
        self.assertEqual(ideal_laps(sample)[0]["ideal_seconds"], 89)
        self.assertEqual(ideal_laps(sample)[0]["best_recorded_seconds"], 90)

    def test_sector_pace(self):
        self.assertEqual(sector_pace([
            {"driver_number": 1, "duration_sector_1": 30},
            {"driver_number": 1, "duration_sector_1": 32}
        ])[0]["sector_1_median_seconds"], 31)

    def test_trend(self):
        data = [{"driver_number": 1, "lap_number": i, "lap_duration": 90 + i}
                for i in range(1, 6)]
        self.assertEqual(lap_trends(data)[0]["slope_seconds_per_lap"], 1)
        with self.assertRaises(ValueError):
            lap_trends([], min_laps=1)

    def test_compounds(self):
        laps = [{"driver_number": 1, "lap_number": 1, "lap_duration": 90},
                {"driver_number": 1, "lap_number": 2, "lap_duration": 92},
                {"driver_number": 1, "lap_number": 3, "lap_duration": 93}]
        stints = [{"driver_number": 1, "lap_start": 1, "lap_end": 2,
                   "compound": "SOFT"},
                  {"driver_number": 1, "lap_start": 3, "lap_end": 3,
                   "compound": "HARD"}]
        self.assertEqual(len(compound_pace(laps, stints)), 2)
        self.assertEqual(stint_strategies(stints)[0]["stint_laps"], [2, 1])

    def test_pit_histogram(self):
        self.assertEqual(pit_window_histogram([
            {"lap_number": 20}, {"lap_number": 20}, {"lap_number": 22}
        ])[0]["pit_entries"], 2)

    def test_speed(self):
        stats = speed_summary([{"driver_number": 44, "speed": 300},
                               {"driver_number": 44, "speed": 320}])
        self.assertEqual(stats[0]["maximum_kmh"], 320)

    def test_pedals(self):
        result = throttle_brake_summary([
            {"driver_number": 1, "throttle": 100, "brake": 0},
            {"driver_number": 1, "throttle": 50, "brake": 100},
        ])[0]
        self.assertEqual(result["full_throttle_sample_pct"], 50)
        self.assertEqual(result["brake_engaged_sample_pct"], 50)

    def test_drs(self):
        result = drs_code_summary([
            {"driver_number": 1, "drs": 12},
            {"driver_number": 1, "drs": 8},
        ])[0]
        self.assertEqual(result["code_10_12_14_pct"], 50)

    def test_weather(self):
        result = weather_summary([
            {"track_temperature": 25, "rainfall": 0},
            {"track_temperature": 30, "rainfall": 1},
        ])
        self.assertEqual(result["mean_track_temperature"], 27.5)
        self.assertEqual(result["rainfall_reported_samples"], 1)

    def test_race_control(self):
        result = race_control_summary([
            {"category": "Flag", "flag": "YELLOW"},
            {"category": "Flag", "flag": "GREEN"},
        ])
        self.assertEqual(result["by_category"]["Flag"], 2)

    def test_lap_deltas(self):
        result = lap_deltas([
            {"driver_number": 1, "lap_number": 1, "lap_duration": 95},
            {"driver_number": 2, "lap_number": 1, "lap_duration": 94},
        ], 1, 2)
        self.assertEqual(result[0]["delta_a_minus_b_seconds"], 1)

    def test_position_trajectory(self):
        result = position_trajectory([
            {"driver_number": 44, "date": "2025-11-01T10:00:02", "position": 2},
            {"driver_number": 44, "date": "2025-11-01T10:00:01", "position": 4},
            {"driver_number": 44, "date": "2025-11-01T10:00:03", "position": 2},
        ], 44)
        self.assertEqual([p["position"] for p in result], [4, 2])


if __name__ == "__main__":
    unittest.main()
