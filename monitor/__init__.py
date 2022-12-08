
class Capture(object):

    totalMinutes = None
    totalSeconds = None
    distance = None
    minutesTo500m = None
    secondsTo500m = None
    strokesPerMinute = None
    watt = None
    calorinesPerHour = None
    level = None

    def __init__(self, raw):
        assert raw[0]=='A'
        self.totalMinutes = int(raw[3:5], base=10)
        self.totalSeconds = int(raw[5:7], base=10)
        self.distance = int(raw[7:12], base=10)
        self.strokesPerMinute = int(raw[17:20], base=10)
        self.watt = int(raw[20:23], base=10)
        self.calorinesPerHour = int(raw[23:27], base=10)
        self.level = int(raw[27:29], base=10)
        