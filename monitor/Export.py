import datetime
import xml.etree.ElementTree as ET
from io import BytesIO
from statistics import harmonic_mean

from monitor import Capture

XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
TCD_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
AE_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"

class Export(object):

    _isInitialized : bool = False
    _root = None
    _id = None
    _lap = None
    _totalTimeSeconds = None
    _distanceMeters = None
    _calories = None
    _intensity = None
    _avg_heartrate_value = None
    _max_heartrate_value = None
    _triggerMethod = None
    _track = None
    _caloriesPerHour = {}
    _heartrates = {}
    _external_heartrates = {}

    def __init__(self):
        builder = ET.TreeBuilder()
        ET.register_namespace("", TCD_NS)
        ET.register_namespace("xsi", XSI_NS)
        ET.register_namespace("ae", AE_NS)
        builder.start("{" + TCD_NS + "}TrainingCenterDatabase", {})
        builder.start("Activities", {})
        builder.start("Activity", {"Sport": "Other"})
        self._id = self._add_empty(builder, "Id")
        self._lap = builder.start("Lap", {})
        self._totalTimeSeconds = self._add_empty(builder, "TotalTimeSeconds")
        self._distanceMeters = self._add_empty(builder, "DistanceMeters")
        self._calories = self._add_empty(builder, "Calories")
        self._avg_heartrate_value = Export._add_value_element(self._lap, "AverageHeartRateBpm")
        self._max_heartrate_value = Export._add_value_element(self._lap, "MaximumHeartRateBpm")
        self._intensity = self._add_empty(builder, "Intensity")
        self._triggerMethod = self._add_empty(builder, "TriggerMethod")
        self._track = builder.start("Track", {})
        builder.end("Track")
        extensions = builder.start("Extensions", {})
        self._root = builder.close()
        lx = ET.SubElement(extensions, "{" + AE_NS + "}LX")
        self._maxWatts = ET.SubElement(lx, "{" + AE_NS + "}MaxWatts")

    def load_heartratebpm(self, filename: str):
        self._external_heartrates = {}
        tree = ET.parse(filename)
        for trackpoint in tree.findall(".//{" + TCD_NS + "}Trackpoint[{" + TCD_NS + "}HeartRateBpm]"):
            iso_time = trackpoint.find("{" + TCD_NS + "}Time").text
            heartratebpm = trackpoint.find("{" + TCD_NS + "}HeartRateBpm/{" + TCD_NS + "}Value").text
            self._external_heartrates[iso_time] = heartratebpm


    def add_trackpoint(self, capture: Capture):
        """

        :return:
        """
        #
        if not self._isInitialized:
            self._init(capture)

        total_time_seconds = capture.totalMinutes*60 + capture.totalSeconds
        iso_time = self._get_formatted_time(capture.time)

        self._totalTimeSeconds.text = str(total_time_seconds)
        self._distanceMeters.text = str(capture.distance)
        self._caloriesPerHour[total_time_seconds] = capture.caloriesPerHour

        trackpoint = ET.SubElement(self._track, "Trackpoint")

        time = ET.SubElement(trackpoint, "Time")
        time.text = iso_time

        distance_meters = ET.SubElement(trackpoint, "DistanceMeters")
        distance_meters.text = str(capture.distance)

        cadence = ET.SubElement(trackpoint, "Cadence")
        cadence.text = str(capture.strokesPerMinute)

        if iso_time in self._external_heartrates:
            bpm = self._external_heartrates[iso_time]
            Export._add_value_element(trackpoint, "HeartRateBpm", bpm)
            self._heartrates[total_time_seconds] = int(bpm)
        elif len(self._external_heartrates) > 0:
            print("No heart rate for: " + iso_time)

        extensions = ET.SubElement(trackpoint, "Extensions")
        tpx = ET.SubElement(extensions, "{" + AE_NS + "}TPX")
        watts = ET.SubElement(tpx, "{" + AE_NS + "}Watts")
        watts.text = str(capture.watt)

        if not self._maxWatts.text:
            self._maxWatts.text = str(capture.watt)
        else:
            self._maxWatts.text = str(max(int(self._maxWatts.text), capture.watt))

    def _init(self, first_capture: Capture):
        self._intensity.text = "Active"
        self._triggerMethod.text = "Manual"

        start_time = first_capture.time - datetime.timedelta(seconds=first_capture.totalSeconds)
        formatted_start_time = self._get_formatted_time(start_time)
        self._id.text = formatted_start_time
        self._lap.attrib["StartTime"] = formatted_start_time

        self._isInitialized = True

    def _post_processing(self):
        self._update_calories()
        self._update_heartrate_stats()

    def _update_calories(self):
        calphs = {}
        elapsed_seconds = 0
        for second, calph in self._caloriesPerHour.items():
            calphs[calph] = calphs.get(calph, 0) + second - elapsed_seconds
            elapsed_seconds = second
        mean = harmonic_mean(calphs.keys(), weights=calphs.values())
        total_time_hours = int(self._totalTimeSeconds.text) / 3600
        self._calories.text = str(round(mean * total_time_hours))

    def _update_heartrate_stats(self):
        heartrates = {}
        elapsed_seconds = 0
        for second, bpm in self._heartrates.items():
            heartrates[bpm] = heartrates.get(bpm, 0) + second - elapsed_seconds
            elapsed_seconds = second
        mean = harmonic_mean(heartrates.keys(), weights=heartrates.values())
        self._avg_heartrate_value.text = str(round(mean))
        self._max_heartrate_value.text = str(max(heartrates.keys()))

    def write(self, f):
        self._post_processing()
        ET.indent(self._root, space="\t", level=0)
        ET.ElementTree(self._root).write(f, encoding='utf-8', method="xml",xml_declaration=True)

    def tostring(self):
        self._post_processing()
        result = BytesIO()
        ET.indent(self._root, space="\t", level=0)
        ET.ElementTree(self._root).write(result, encoding='utf-8', method="xml",xml_declaration=True)
        return result.getvalue().decode()

    @staticmethod
    def _get_formatted_time(time: datetime):
        return time.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _add_empty(builder, tag):
        builder.start(tag, {})
        return builder.end(tag)

    @staticmethod
    def _add_value_element(parent, tag, value=''):
        element = ET.SubElement(parent, tag)
        value_element = ET.SubElement(element, "Value")
        value_element.text = value
        return value_element
