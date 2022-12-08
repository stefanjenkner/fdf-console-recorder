import unittest

from monitor import Capture

class TestSum(unittest.TestCase):
    def test_parse(self):
        """
        ...
        """
        input = "A8001340038410210033165086504"
        capture = Capture(input)
        self.assertEqual(capture.totalMinutes, 1)
        self.assertEqual(capture.totalSeconds, 34)
        self.assertEqual(capture.distance, 384)
        self.assertEqual(capture.strokesPerMinute, 33)
        self.assertEqual(capture.watt, 165)
        self.assertEqual(capture.calorinesPerHour, 865)
        self.assertEqual(capture.level, 4)
        print(repr(capture))

if __name__ == '__main__':
    unittest.main()