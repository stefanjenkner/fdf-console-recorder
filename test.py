#!/usr/bin/env python

import datetime
import unittest

import fitdecode

from monitor.Capture import Capture
from monitor.DataFrame import DataFrame
from monitor.Export import Export


class TestParse(unittest.TestCase):

    def test_parse(self):
        capture = Capture(1670609153225, "A8001340038410210033165086504")

        self.assertEqual(datetime.datetime(2022, 12, 9, 19, 5, 53, 0), capture.time)
        self.assertEqual(94, capture.elapsed_time.total_seconds())
        self.assertEqual(384, capture.distance)
        self.assertEqual(130, capture.time_to_500m.total_seconds())
        self.assertEqual(33, capture.strokes_per_minute)
        self.assertEqual(165, capture.watt)
        self.assertEqual(865, capture.calories_per_hour)
        self.assertEqual(4, capture.level)


class TestExport(unittest.TestCase):

    def test_export_write_sample1(self):
        export = Export()
        with open("samples/1670609153225.txt", encoding='utf-8') as f:
            for line in f.readlines():
                (milliseconds, data) = line.split(" ")
                export.add_track_point(Capture(int(milliseconds), data))
        with open("samples/1670609153225.tcx", 'wb') as f:
            export.write(f)

    def test_export_write_sample2(self):
        export = Export()
        with open("samples/1670790032608.txt", encoding='utf-8') as f:
            for line in f.readlines():
                (milliseconds, data) = line.split(" ")
                export.add_track_point(Capture(int(milliseconds), data))
        with open("samples/1670790032608.tcx", 'wb') as f:
            export.write(f)

    def test_enhance_export_write_sample1(self):
        export = Export()
        export.load_heart_rate_from_tcx("samples/1670609153225_watch.tcx")
        with open("samples/1670609153225.txt", encoding='utf-8') as f:
            for line in f.readlines():
                (milliseconds, data) = line.split(" ")
                export.add_track_point(Capture(int(milliseconds), data))
        with open("samples/1670609153225_enhanced.tcx", 'wb') as f:
            export.write(f)

    def test_enhance_export_write_sample2(self):
        export = Export()
        export.load_heart_rate_from_fit("samples/1670790032608_watch.fit")
        with open("samples/1670790032608.txt", encoding='utf-8') as f:
            for line in f.readlines():
                (milliseconds, data) = line.split(" ")
                export.add_track_point(Capture(int(milliseconds), data))
        with open("samples/1670790032608_enhanced.tcx", 'wb') as f:
            export.write(f)


class TestDataFrame(unittest.TestCase):

    def setUp(self) -> None:
        self.__external_heart_rates = {}

        with fitdecode.FitReader('samples/1670790032608_watch.fit') as fit:
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                    timestamp = list(filter(lambda x: x.name == 'timestamp', frame.fields))[0].value
                    heart_rate = list(filter(lambda x: x.name == 'heart_rate', frame.fields))[0].value
                    self.__external_heart_rates[timestamp] = int(heart_rate)

    def test_interpolate(self):
        start = min(self.__external_heart_rates.keys())
        frame = DataFrame()
        frame.load_from_dict(self.__external_heart_rates, 'BPM')
        frame.interpolate('BPM', 'BPM_nearest', method='nearest')
        frame.interpolate('BPM', 'BPM_linear', method='linear')
        self.assertEqual(82.0, frame.get(start, 'BPM'))
        self.assertEqual(82.0, frame.get(start, 'BPM_nearest'))
        self.assertEqual(82.0, frame.get(start, 'BPM_linear'))

    def test_mean(self):
        start = min(self.__external_heart_rates.keys())
        end = max(self.__external_heart_rates.keys())
        frame = DataFrame()
        frame.load_from_dict(self.__external_heart_rates, 'BPM')
        frame.interpolate('BPM', 'BPM_linear', method='linear')
        self.assertEqual(138.34, round(frame.mean(start, end, 'BPM'), 2))
        self.assertEqual(138.67, round(frame.mean(start, end, 'BPM_linear'), 2))

    def test_max(self):
        start = min(self.__external_heart_rates.keys())
        end = max(self.__external_heart_rates.keys())
        frame = DataFrame()
        frame.load_from_dict(self.__external_heart_rates, 'BPM')
        expected = max(self.__external_heart_rates.values())
        self.assertEqual(expected, frame.max(start, end, 'BPM'))


if __name__ == '__main__':
    unittest.main()
