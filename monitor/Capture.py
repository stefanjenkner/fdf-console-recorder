from datetime import datetime


class Capture(object):

    time: datetime = None
    totalMinutes = None
    totalSeconds = None
    distance = None
    minutesTo500m = None
    secondsTo500m = None
    strokesPerMinute = None
    watt = None
    caloriesPerHour = None
    level = None

    def __init__(self, milliseconds: int, raw: str):
        assert raw[0]=='A'
        self.time = datetime.fromtimestamp(milliseconds/1000)
        self.totalMinutes = int(raw[3:5], base=10)
        self.totalSeconds = int(raw[5:7], base=10)
        self.distance = int(raw[7:12], base=10)
        self.strokesPerMinute = int(raw[17:20], base=10)
        self.watt = int(raw[20:23], base=10)
        self.caloriesPerHour = int(raw[23:27], base=10)
        self.level = int(raw[27:29], base=10)