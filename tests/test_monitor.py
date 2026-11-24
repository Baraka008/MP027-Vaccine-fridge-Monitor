import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from monitor import (
    build_daily_summary,
    compare_file_sizes,
    detect_excursions,
    generate_readings,
    is_out_of_range,
    save_edge_summary,
)


class TemperatureMonitorTests(unittest.TestCase):
    def test_temperature_limits_are_inclusive(self):
        self.assertFalse(is_out_of_range(2.0))
        self.assertFalse(is_out_of_range(8.0))
        self.assertTrue(is_out_of_range(1.9))
        self.assertTrue(is_out_of_range(8.1))

    def test_cat_hand_checked_excursion_is_ten_minutes(self):
        start = datetime(2026, 1, 1, 8, 0)
        readings = [
            {"timestamp": start, "temperature_c": 8.4},
            {"timestamp": start + timedelta(minutes=5), "temperature_c": 8.6},
            {"timestamp": start + timedelta(minutes=10), "temperature_c": 7.9},
        ]
        events = detect_excursions(readings)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["duration_minutes"], 10)
        self.assertEqual(events[0]["peak_temperature_c"], 8.6)
        self.assertEqual(events[0]["end"], start + timedelta(minutes=10))

    def test_consecutive_excursion_samples_form_one_event(self):
        start = datetime(2026, 1, 1)
        readings = [
            {"timestamp": start + timedelta(minutes=5 * i), "temperature_c": t}
            for i, t in enumerate([5.0, 8.4, 8.6, 7.9, 5.0])
        ]
        events = detect_excursions(readings)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["duration_minutes"], 10)

    def test_generator_is_seeded_and_has_4032_samples(self):
        self.assertEqual(generate_readings(), generate_readings())
        self.assertEqual(len(generate_readings()), 4032)

    def test_edge_summary_is_smaller_than_raw_log(self):
        readings = generate_readings()
        events = detect_excursions(readings)
        daily = build_daily_summary(readings, events)
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "raw.csv"
            edge = Path(temp) / "edge.csv"
            raw.write_text(
                "timestamp,temperature_c\n" +
                "2026-01-01 00:00:00,5.0\n" * 4032,
                encoding="utf-8",
            )
            save_edge_summary(daily, edge)
            sizes = compare_file_sizes(raw, edge)
            self.assertLess(sizes["edge_bytes"], sizes["raw_bytes"])


if __name__ == "__main__":
    unittest.main()
