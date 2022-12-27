import datetime
import xml.etree.ElementTree as ET

import fitdecode as fitdecode

from console.Capture import Capture
from console.DataFrame import DataFrame

SPEED = "Speed"
WATT = "Watt"
SPM = "SPM"
DISTANCE = "Distance"
CALPH = "CalPH"
CALPH_LINEAR = "CalPH_"
BPM = 'BPM'
BPM_LINEAR = 'BPM_'

XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
TCD_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
AE_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"


class Export(object):
    __is_initialized: bool
    __start: datetime
    __end: datetime
    __frame: DataFrame
    __watts: dict[datetime, int]
    __calories_per_hour: dict[datetime, int]
    __distance_meters: dict[datetime, int]
    __strokes_per_minute: dict[datetime, int]
    __speeds: dict[datetime, float]

    def __init__(self):

        self.__is_initialized = False
        self.__start, self.__end = (None, None)
        self.__frame = DataFrame()
        self.__watts = {}
        self.__calories_per_hour = {}
        self.__distance_meters = {}
        self.__strokes_per_minute = {}
        self.__speeds = {}

        ET.register_namespace("", TCD_NS)
        ET.register_namespace("xsi", XSI_NS)
        ET.register_namespace("ae", AE_NS)

    def load_heart_rate_from_tcx(self, filename: str):
        """Load external HR data from TCX file."""
        external_heart_rates: dict[datetime.datetime, int] = {}
        tree = ET.parse(filename)
        for track_point in tree.findall(".//{" + TCD_NS + "}Trackpoint[{" + TCD_NS + "}HeartRateBpm]"):
            almost_iso_time = track_point.find("{" + TCD_NS + "}Time").text
            iso_time = almost_iso_time.replace('Z', '+00:00')
            timestamp = datetime.datetime.fromisoformat(iso_time)
            bpm = track_point.find("{" + TCD_NS + "}HeartRateBpm/{" + TCD_NS + "}Value").text
            external_heart_rates[timestamp] = int(bpm)
        self.__frame.load_from_dict(external_heart_rates, BPM)
        self.__frame.interpolate(BPM, BPM_LINEAR, method='linear')

    def load_heart_rate_from_fit(self, filename: str):
        """Load external HR data from FIT file."""
        external_heart_rates: dict[datetime.datetime, int] = {}
        with fitdecode.FitReader(filename) as fit:
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                    timestamp = list(filter(lambda x: x.name == 'timestamp', frame.fields))[0].value
                    heart_rate = list(filter(lambda x: x.name == 'heart_rate', frame.fields))[0].value
                    external_heart_rates[timestamp] = int(heart_rate)
        self.__frame.load_from_dict(external_heart_rates, BPM)
        self.__frame.interpolate(BPM, BPM_LINEAR, method='linear')

    def add_track_point(self, capture: Capture):
        """"""
        if not self.__is_initialized:
            self.__start = capture.utc_time - capture.elapsed_time
            self.__is_initialized = True
        if not self.__end or capture.utc_time > self.__end:
            self.__end = capture.utc_time

        self.__calories_per_hour[capture.utc_time] = capture.calories_per_hour
        self.__distance_meters[capture.utc_time] = capture.distance
        self.__strokes_per_minute[capture.utc_time] = capture.strokes_per_minute
        try:
            meters_per_second = 500 / capture.time_to_500m.total_seconds()
        except ZeroDivisionError:
            meters_per_second = 0.0
        self.__speeds[capture.utc_time] = round(meters_per_second, 2)
        self.__watts[capture.utc_time] = capture.watt

    def write(self, f):
        self.__frame.load_from_dict(self.__distance_meters, DISTANCE)
        self.__frame.load_from_dict(self.__strokes_per_minute, SPM)
        self.__frame.load_from_dict(self.__speeds, SPEED)
        self.__frame.load_from_dict(self.__watts, WATT)

        root = ET.Element("{" + TCD_NS + "}TrainingCenterDatabase", {})
        activities = ET.SubElement(root, "Activities")
        activity = ET.SubElement(activities, "Activity", {"Sport": "Other"})
        id_ = ET.SubElement(activity, "Id")
        id_.text = Export.__get_formatted_time(self.__start)

        lap = ET.SubElement(activity, "Lap")
        lap.attrib["StartTime"] = Export.__get_formatted_time(self.__start)
        self.__add_total_time_seconds(lap)
        self.__add_distance_meters(lap)
        self.__add_max_speed(lap)
        self.__add_calories(lap)
        self.__add_heart_rate_stats(lap)
        Export.__add_intensity_and_trigger_method(lap)

        track = ET.SubElement(lap, "Track", {})
        self.__frame.apply(self.__start, self.__end, Export.__add_track_point_to_track, track,
                           dropnan_columns=[DISTANCE, SPM])

        extensions = ET.SubElement(lap, "Extensions", {})
        lx = ET.SubElement(extensions, "{" + AE_NS + "}LX")
        self.__add_speed_stats(lx)
        self.__add_watt_stats(lx)

        self.__frame.pprint(self.__start, self.__end)
        ET.indent(root, space="\t", level=0)
        ET.ElementTree(root).write(f, encoding='utf-8', method="xml", xml_declaration=True)

    @staticmethod
    def __add_track_point_to_track(row, track):

        track_point = ET.SubElement(track, "Trackpoint")
        time = ET.SubElement(track_point, "Time")
        time.text = Export.__get_formatted_time(row.name)
        distance_meters = ET.SubElement(track_point, "DistanceMeters")
        distance_meters.text = str(round(row[DISTANCE]))
        cadence = ET.SubElement(track_point, "Cadence")
        cadence.text = str(round(row[SPM]))
        try:
            bpm = round(row[BPM_LINEAR])
            Export.__add_value_element(track_point, "HeartRateBpm", str(bpm))
        except KeyError:
            pass
        except ValueError:
            pass
        extensions = ET.SubElement(track_point, "Extensions")
        tpx = ET.SubElement(extensions, "{" + AE_NS + "}TPX")
        speed = ET.SubElement(tpx, "{" + AE_NS + "}Speed")
        speed.text = f'{row[SPEED]:.02f}'
        watts = ET.SubElement(tpx, "{" + AE_NS + "}Watts")
        watts.text = str(round(row[WATT]))
        return track_point

    def __add_total_time_seconds(self, lap):
        total_seconds = (self.__end - self.__start).total_seconds()
        total_time_seconds = ET.SubElement(lap, "TotalTimeSeconds")
        total_time_seconds.text = str(round(total_seconds))

    def __add_distance_meters(self, lap):
        distance = self.__frame.max(self.__start, self.__end, DISTANCE)
        distance_meters = ET.SubElement(lap, "DistanceMeters")
        distance_meters.text = str(int(distance))

    def __add_max_speed(self, lap):
        maximum = self.__frame.max(self.__start, self.__end, SPEED)
        maximum_speed = ET.SubElement(lap, "MaximumSpeed")
        maximum_speed.text = f'{maximum:.02f}'

    def __add_calories(self, lap):
        self.__frame.load_from_dict(self.__calories_per_hour, CALPH)
        self.__frame.interpolate(CALPH, CALPH_LINEAR, method="linear")
        mean = self.__frame.mean(self.__start, self.__end, CALPH_LINEAR)
        calories = ET.SubElement(lap, "Calories")
        total_time_hours = (self.__end - self.__start).total_seconds() / 3600
        calories.text = str(round(mean * total_time_hours))

    def __add_heart_rate_stats(self, lap):
        try:
            mean = self.__frame.mean(self.__start, self.__end, BPM_LINEAR)
            maximum = self.__frame.max(self.__start, self.__end, BPM)
            Export.__add_value_element(lap, "AverageHeartRateBpm", value=str(round(mean)))
            Export.__add_value_element(lap, "MaximumHeartRateBpm", value=str(round(maximum)))
        except KeyError:
            pass

    @staticmethod
    def __add_intensity_and_trigger_method(lap):
        intensity = ET.SubElement(lap, "Intensity")
        intensity.text = "Active"
        trigger_method = ET.SubElement(lap, "TriggerMethod")
        trigger_method.text = "Manual"

    def __add_speed_stats(self, lx):
        avg_speed = ET.SubElement(lx, "{" + AE_NS + "}AvgSpeed")
        avg_speed.text = f'{self.__frame.mean(self.__start, self.__end, SPEED):.02f}'

    def __add_watt_stats(self, lx):
        avg_watts = ET.SubElement(lx, "{" + AE_NS + "}AvgWatts")
        avg_watts.text = str(round(self.__frame.mean(self.__start, self.__end, WATT)))
        max_watts = ET.SubElement(lx, "{" + AE_NS + "}MaxWatts")
        max_watts.text = str(round(self.__frame.max(self.__start, self.__end, WATT)))

    @staticmethod
    def __get_formatted_time(time: datetime):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def __add_value_element(parent, tag, value=''):
        element = ET.SubElement(parent, tag)
        value_element = ET.SubElement(element, "Value")
        value_element.text = value
        return value_element
