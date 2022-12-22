from datetime import datetime, timedelta, timezone


class Capture(object):

    time: datetime = None
    utc_time: datetime = None
    elapsed_time: timedelta = None
    distance: int = None

    time_to_500m: timedelta = None
    strokes_per_minute: int = None
    watt: int = None
    calories_per_hour: int = None

    level: int = None

    def __init__(self, milliseconds: int, raw: str):
        assert raw[0] == 'A'

        self.utc_time = datetime.fromtimestamp(int(milliseconds / 1000), tz=timezone.utc)

        total_minutes = int(raw[3:5], base=10)
        total_seconds = int(raw[5:7], base=10)
        self.elapsed_time = timedelta(minutes=total_minutes, seconds=total_seconds)

        self.distance = int(raw[7:12], base=10)

        minutes_to_500m = int(raw[13:15], base=10)
        seconds_to_500m = int(raw[15:17], base=10)
        self.time_to_500m = timedelta(minutes=minutes_to_500m, seconds=seconds_to_500m)

        self.strokes_per_minute = int(raw[17:20], base=10)

        self.watt = int(raw[20:23], base=10)

        self.calories_per_hour = int(raw[23:27], base=10)

        self.level = int(raw[27:29], base=10)
