import unittest

from monitor import Capture, Export
from datetime import datetime

class TestSum(unittest.TestCase):

    def test_parse(self):
        capture = Capture(1670609153225, "A8001340038410210033165086504")
        self.assertEqual(datetime(2022, 12, 9, 19, 5, 53, 225000), capture.time)
        self.assertEqual(1, capture.totalMinutes)
        self.assertEqual(34, capture.totalSeconds)
        self.assertEqual(384, capture.distance)
        self.assertEqual(33, capture.strokesPerMinute)
        self.assertEqual(165, capture.watt)
        self.assertEqual(865, capture.caloriesPerHour)
        self.assertEqual(4, capture.level)

    def test_export_tostring(self):
        export = Export()
        with open("samples/1670609153225.txt", encoding='utf-8') as f:
            for line in f.readlines():
                (milliseconds, data) = line.split(" ")
                export.add_trackpoint(Capture(int(milliseconds), data))
        print(export.tostring())

    def test_export_write(self):
        export = Export()
        with open("samples/1670609153225.txt", encoding='utf-8') as f:
            for line in f.readlines():
                (milliseconds, data) = line.split(" ")
                export.add_trackpoint(Capture(int(milliseconds), data))
        with open("samples/1670609153225.tcx", 'wb') as f:
            export.write(f)

    def test_export_enhance(self):
        export = Export()
        export.load_heartratebpm("samples/1670609153225_watch.tcx")
        with open("samples/1670609153225.txt", encoding='utf-8') as f:
            for line in f.readlines():
                (milliseconds, data) = line.split(" ")
                export.add_trackpoint(Capture(int(milliseconds), data))
        with open("samples/1670609153225_enhanced.tcx", 'wb') as f:
            export.write(f)

if __name__ == '__main__':
    unittest.main()
