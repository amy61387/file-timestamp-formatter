import datetime as dt
import os
import tempfile
import unittest

from file_timestamp_formatter import FileTimestampFormatter, format_stat_time


class TestOffsetValidation(unittest.TestCase):
    def test_zero_offset_is_allowed(self):
        f = FileTimestampFormatter(0)
        self.assertEqual(f.offset_minutes, 0)

    def test_negative_offset_allowed(self):
        f = FileTimestampFormatter(-480)
        self.assertEqual(f.offset_minutes, -480)

    def test_positive_offset_allowed(self):
        f = FileTimestampFormatter(540)
        self.assertEqual(f.offset_minutes, 540)

    def test_boundary_minus_1440_allowed(self):
        f = FileTimestampFormatter(-1440)
        self.assertEqual(f.offset_minutes, -1440)

    def test_boundary_plus_1440_allowed(self):
        f = FileTimestampFormatter(1440)
        self.assertEqual(f.offset_minutes, 1440)

    def test_out_of_range_negative_rejected(self):
        with self.assertRaises(ValueError):
            FileTimestampFormatter(-1441)

    def test_out_of_range_positive_rejected(self):
        with self.assertRaises(ValueError):
            FileTimestampFormatter(1441)

    def test_non_int_rejected(self):
        with self.assertRaises(TypeError):
            FileTimestampFormatter(0.0)


class TestFormat(unittest.TestCase):
    def test_known_utc_epoch(self):
        f = FileTimestampFormatter(0)
        # 1970-01-01T00:00:00+00:00
        self.assertEqual(f.format(0.0), "1970-01-01T00:00:00+00:00")

    def test_known_positive_offset(self):
        # +09:00 is JST; 9 hours = 540 minutes
        f = FileTimestampFormatter(540)
        self.assertEqual(f.format(0.0), "1970-01-01T09:00:00+09:00")

    def test_known_negative_offset(self):
        # -08:00 is PST; 8 hours = 480 minutes
        f = FileTimestampFormatter(-480)
        self.assertEqual(f.format(0.0), "1969-12-31T16:00:00-08:00")

    def test_microsecond_timespec(self):
        f = FileTimestampFormatter(0)
        # 123456 microseconds = 0.123456 seconds
        result = f.format(0.123456, timespec="microseconds")
        self.assertEqual(result, "1970-01-01T00:00:00.123456+00:00")

    def test_seconds_timespec_truncates_fraction(self):
        f = FileTimestampFormatter(0)
        result = f.format(0.999999, timespec="seconds")
        self.assertEqual(result, "1970-01-01T00:00:00+00:00")

    def test_pre_epoch_in_utc(self):
        # -1 second before epoch
        f = FileTimestampFormatter(0)
        self.assertEqual(f.format(-1.0), "1969-12-31T23:59:59+00:00")


class TestFormatStat(unittest.TestCase):
    def test_format_stat_returns_three_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f")
            with open(p, "w") as fh:
                fh.write("x")
            st = os.stat(p)
            f = FileTimestampFormatter(0)
            result = f.format_stat(st)
            self.assertIsInstance(result, dict)
            self.assertEqual(set(result.keys()), {"atime", "mtime", "ctime"})

    def test_format_stat_values_are_iso_strings(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f")
            with open(p, "w") as fh:
                fh.write("x")
            st = os.stat(p)
            f = FileTimestampFormatter(0)
            result = f.format_stat(st)
            for key in ("atime", "mtime", "ctime"):
                # parse it back to confirm it's a real ISO 8601 value
                parsed = dt.datetime.fromisoformat(result[key])
                self.assertIsInstance(parsed, dt.datetime)

    def test_format_stat_microseconds(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f")
            with open(p, "w") as fh:
                fh.write("x")
            st = os.stat(p)
            f = FileTimestampFormatter(0)
            result = f.format_stat(st, timespec="microseconds")
            for key in ("atime", "mtime", "ctime"):
                parsed = dt.datetime.fromisoformat(result[key])
                self.assertIsInstance(parsed, dt.datetime)


class TestModuleFunction(unittest.TestCase):
    def test_module_function_matches_instance(self):
        inst = FileTimestampFormatter(540).format(0.0)
        fn = format_stat_time(0.0, 540)
        self.assertEqual(inst, fn)

    def test_module_function_default_offset(self):
        self.assertEqual(format_stat_time(0.0), "1970-01-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
