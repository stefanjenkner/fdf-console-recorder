import datetime
import xml.etree.ElementTree as ET
from io import BytesIO

import fitdecode as fitdecode

from monitor.Capture import Capture
from monitor.TimeSeries import TimeSeries

XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
TCD_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
AE_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"


class Export(object):
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
    _heart_rates = {}
    _external_heart_rates = {}
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
        self._external_heart_rates = {}
        tree = ET.parse(filename)
        for trackpoint in tree.findall(".//{" + TCD_NS + "}Trackpoint[{" + TCD_NS + "}HeartRateBpm]"):
            iso_time = trackpoint.find("{" + TCD_NS + "}Time").text
            bpm = trackpoint.find("{" + TCD_NS + "}HeartRateBpm/{" + TCD_NS + "}Value").text
            self._external_heart_rates[iso_time] = int(bpm)

    def load_heart_rate_from_fit(self, filename: str):
        self._external_heart_rates = {}
        with fitdecode.FitReader(filename) as fit:
            for frame in fit:
                if frame.frame_type == fitdecode.FIT_FRAME_DATA and frame.name == "record":
                    timestamp = list(filter(lambda x: x.name == 'timestamp', frame.fields))[0].value
                    heart_rate = list(filter(lambda x: x.name == 'heart_rate', frame.fields))[0].value
                    iso_time = timestamp.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    self._external_heart_rates[iso_time] = int(heart_rate)

    def add_trackpoint(self, capture: Capture):
        """

        :return:
        """
        #
        if not self._isInitialized:
            self._init(capture)

        total_time_seconds = int(capture.elapsed_time.total_seconds())
        iso_time = self._get_formatted_time(capture.time)

        self._totalTimeSeconds.text = str(total_time_seconds)
        self._distanceMeters.text = str(capture.distance)
        self._calories_per_hour[total_time_seconds] = capture.calories_per_hour

        trackpoint = ET.SubElement(self._track, "Trackpoint")

        time = ET.SubElement(trackpoint, "Time")
        time.text = iso_time

        distance_meters = ET.SubElement(trackpoint, "DistanceMeters")
        distance_meters.text = str(capture.distance)

        cadence = ET.SubElement(trackpoint, "Cadence")
        cadence.text = str(capture.strokes_per_minute)

        if iso_time in self._external_heart_rates:
            bpm = self._external_heart_rates[iso_time]
            Export._add_value_element(trackpoint, "HeartRateBpm", str(bpm))
            self._heart_rates[total_time_seconds] = bpm
        elif len(self._external_heart_rates) > 0:
            print("No heart rate for: " + iso_time)

        extensions = ET.SubElement(trackpoint, "Extensions")
        tpx = ET.SubElement(extensions, "{" + AE_NS + "}TPX")

        try:
            meters_per_second = 500 / capture.time_to_500m.total_seconds()
        except ZeroDivisionError:
            meters_per_second = 0.0
        self._speeds[total_time_seconds] = round(meters_per_second, 2)
        speed = ET.SubElement(tpx, "{" + AE_NS + "}Speed")
        speed.text = f'{meters_per_second:.02f}'

        watts = ET.SubElement(tpx, "{" + AE_NS + "}Watts")
        watts.text = str(capture.watt)
        self._watts[total_time_seconds] = capture.watt

    def _init(self, first_capture: Capture):
        self._intensity.text = "Active"
        self._triggerMethod.text = "Manual"

        start_time = first_capture.time - first_capture.elapsed_time
        formatted_start_time = self._get_formatted_time(start_time)
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
        if len(self._heart_rates) == 0:
            self._lap.remove(self._avg_heart_rate_value)
            self._lap.remove(self._max_heart_rate_value)
            return
        time_series = TimeSeries(self._heart_rates)
        self._avg_heart_rate_value.find("Value").text = str(round(time_series.get_harmonic_mean()))
        self._max_heart_rate_value.find("Value").text = str(time_series.get_max())

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
        return time.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _add_value_element(parent, tag, value=''):
        element = ET.SubElement(parent, tag)
        value_element = ET.SubElement(element, "Value")
        value_element.text = value
        return element
