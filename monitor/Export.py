import datetime
import xml.etree.ElementTree as ET
from io import BytesIO

import fitdecode as fitdecode

from monitor.Capture import Capture
from monitor.DataFrame import DataFrame
from monitor.TimeSeries import TimeSeries

XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
TCD_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
AE_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"


class Export(object):

    __start: datetime
    __end: datetime
    __frame: DataFrame = None

    _isInitialized: bool = False
    _root = None
    _id = None
    _lap = None
    _totalTimeSeconds = None
    _distanceMeters = None
    _maximum_speed = None
    _calories = None
    _intensity = None
    _avg_heart_rate_value = None
    _max_heart_rate_value = None
    _avg_watts = None
    _max_watts = None
    _avg_speed = None
    _triggerMethod = None
    _track = None

    _calories_per_hour = {}
    _speeds = {}
    _watts = {}

    def __init__(self):

        ET.register_namespace("", TCD_NS)
        ET.register_namespace("xsi", XSI_NS)
        ET.register_namespace("ae", AE_NS)
        self._root = ET.Element("{" + TCD_NS + "}TrainingCenterDatabase", {})
        activities = ET.SubElement(self._root, "Activities")
        activity = ET.SubElement(activities, "Activity", {"Sport": "Other"})
        self._id = ET.SubElement(activity, "Id")
        self._lap = ET.SubElement(activity, "Lap")
        self._totalTimeSeconds = ET.SubElement(self._lap, "TotalTimeSeconds")
        self._distanceMeters = ET.SubElement(self._lap, "DistanceMeters")
        self._maximum_speed = ET.SubElement(self._lap, "MaximumSpeed")
        self._calories = ET.SubElement(self._lap, "Calories")
        self._avg_heart_rate_value = Export._add_value_element(self._lap, "AverageHeartRateBpm")
        self._max_heart_rate_value = Export._add_value_element(self._lap, "MaximumHeartRateBpm")
        self._intensity = ET.SubElement(self._lap, "Intensity")
        self._triggerMethod = ET.SubElement(self._lap, "TriggerMethod")
        self._track = ET.SubElement(self._lap, "Track", {})
        extensions = ET.SubElement(self._lap, "Extensions", {})
        lx = ET.SubElement(extensions, "{" + AE_NS + "}LX")
        self._avg_speed = ET.SubElement(lx, "{" + AE_NS + "}AvgSpeed")
        self._avg_watts = ET.SubElement(lx, "{" + AE_NS + "}AvgWatts")
        self._max_watts = ET.SubElement(lx, "{" + AE_NS + "}MaxWatts")

    def load_heart_rate_from_tcx(self, filename: str):
        """Load external HR data from TCX file."""
        external_heart_rates: dict[datetime.datetime, int] = {}
        tree = ET.parse(filename)
        for trackpoint in tree.findall(".//{" + TCD_NS + "}Trackpoint[{" + TCD_NS + "}HeartRateBpm]"):
            almost_iso_time = trackpoint.find("{" + TCD_NS + "}Time").text
            iso_time = almost_iso_time.replace('Z', '+00:00')
            timestamp = datetime.datetime.fromisoformat(iso_time)
            bpm = trackpoint.find("{" + TCD_NS + "}HeartRateBpm/{" + TCD_NS + "}Value").text
            external_heart_rates[timestamp] = int(bpm)
        self.__frame = DataFrame(min(external_heart_rates.keys()), max(external_heart_rates.keys()))
        self.__frame.load_from_dict(external_heart_rates, 'BPM')
        self.__frame.interpolate('BPM', 'BPM_nearest', method='nearest')
        self.__frame.interpolate('BPM', 'BPM_linear', method='linear')

    def load_heart_rate_from_fit(self, filename: str):
        """Load external HR data from FIT file."""
        external_heart_rates: dict[datetime.datetime, int] = {}
        with fitdecode.FitReader(filename) as fit:
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                    timestamp = list(filter(lambda x: x.name == 'timestamp', frame.fields))[0].value
                    heart_rate = list(filter(lambda x: x.name == 'heart_rate', frame.fields))[0].value
                    external_heart_rates[timestamp] = int(heart_rate)
        self.__frame = DataFrame(min(external_heart_rates.keys()), max(external_heart_rates.keys()))
        self.__frame.load_from_dict(external_heart_rates, 'BPM')
        self.__frame.interpolate('BPM', 'BPM_nearest', method='nearest')
        self.__frame.interpolate('BPM', 'BPM_linear', method='linear')

    def add_trackpoint(self, capture: Capture):
        """"""
        if not self._isInitialized:
            self._init(capture)

        elapsed_time = int(capture.elapsed_time.total_seconds())
        iso_time = self._get_formatted_time(capture.utc_time)
        self.__end = capture.utc_time

        self._totalTimeSeconds.text = str(elapsed_time)
        self._distanceMeters.text = str(capture.distance)
        self._calories_per_hour[elapsed_time] = capture.calories_per_hour

        trackpoint = ET.SubElement(self._track, "Trackpoint")

        time = ET.SubElement(trackpoint, "Time")
        time.text = iso_time

        distance_meters = ET.SubElement(trackpoint, "DistanceMeters")
        distance_meters.text = str(capture.distance)

        cadence = ET.SubElement(trackpoint, "Cadence")
        cadence.text = str(capture.strokes_per_minute)

        if self.__frame:
            #bpm = self.__frame.get(capture.utc_time, 'BPM_nearest')
            bpm = self.__frame.get(capture.utc_time, 'BPM_linear')
            if bpm:
                Export._add_value_element(trackpoint, "HeartRateBpm", str(int(bpm)))
            else:
                print("No heart rate for: " + iso_time)
        else:
            print("No heart rate for: " + iso_time)

        extensions = ET.SubElement(trackpoint, "Extensions")
        tpx = ET.SubElement(extensions, "{" + AE_NS + "}TPX")

        try:
            meters_per_second = 500 / capture.time_to_500m.total_seconds()
        except ZeroDivisionError:
            meters_per_second = 0.0
        self._speeds[elapsed_time] = round(meters_per_second, 2)
        speed = ET.SubElement(tpx, "{" + AE_NS + "}Speed")
        speed.text = f'{meters_per_second:.02f}'

        watts = ET.SubElement(tpx, "{" + AE_NS + "}Watts")
        watts.text = str(capture.watt)
        self._watts[elapsed_time] = capture.watt

    def _init(self, first_capture: Capture):
        self.__start = first_capture.utc_time - first_capture.elapsed_time

        self._intensity.text = "Active"
        self._triggerMethod.text = "Manual"
        formatted_start_time = self._get_formatted_time(self.__start)
        self._id.text = formatted_start_time
        self._lap.attrib["StartTime"] = formatted_start_time

        self._isInitialized = True

    def _post_processing(self):
        self._update_calories()
        self._update_heart_rate_stats()
        self._update_watts_stats()
        self._update_speed_stats()

    def _update_calories(self):
        time_series = TimeSeries(self._calories_per_hour)
        mean = time_series.get_harmonic_mean()
        total_time_hours = int(self._totalTimeSeconds.text) / 3600
        self._calories.text = str(round(mean * total_time_hours))

    def _update_heart_rate_stats(self):
        try:
            mean = self.__frame.mean(self.__start, self.__end, "BPM_linear")
            max = self.__frame.max(self.__start, self.__end, "BPM")
            self._avg_heart_rate_value.find("Value").text = str(round(mean))
            self._max_heart_rate_value.find("Value").text = str(round(max))
        except:
            self._lap.remove(self._avg_heart_rate_value)
            self._lap.remove(self._max_heart_rate_value)

    def _update_watts_stats(self):
        time_series = TimeSeries(self._watts)
        self._avg_watts.text = str(round(time_series.get_harmonic_mean()))
        self._max_watts.text = str(time_series.get_max())

    def _update_speed_stats(self):
        time_series = TimeSeries(self._speeds)
        maximum = time_series.get_max()
        mean = time_series.get_harmonic_mean()
        self._avg_speed.text = f'{mean:.02f}'
        self._maximum_speed.text = f'{maximum:.02f}'

    def write(self, f):
        self._post_processing()
        ET.indent(self._root, space="\t", level=0)
        ET.ElementTree(self._root).write(f, encoding='utf-8', method="xml", xml_declaration=True)

    def tostring(self):
        self._post_processing()
        result = BytesIO()
        ET.indent(self._root, space="\t", level=0)
        ET.ElementTree(self._root).write(result, encoding='utf-8', method="xml", xml_declaration=True)
        return result.getvalue().decode()

    @staticmethod
    def _get_formatted_time(time: datetime):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _add_value_element(parent, tag, value=''):
        element = ET.SubElement(parent, tag)
        value_element = ET.SubElement(element, "Value")
        value_element.text = value
        return element
