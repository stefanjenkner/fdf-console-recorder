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
    _triggerMethod = None
    #_MaximumHeartRateBpmValue = None
    #_AverageHeartRateBpmValue = None
    _track = None
    _heartrates = {}
    _caloriesPerHour = {}

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
        self._intensity = self._add_empty(builder, "Intensity")
        self._triggerMethod = self._add_empty(builder, "TriggerMethod")
        self._track = builder.start("Track", {})
        builder.end("Track")
        extensions = builder.start("Extensions", {})
        self._root = builder.close()
        lx = ET.SubElement(extensions, "{" + AE_NS + "}LX")
        self._maxWatts = ET.SubElement(lx, "{" + AE_NS + "}MaxWatts")

    def load_heartratebpm(self, filename: str):
        self._heartrates = {}
        tree = ET.parse(filename)
        for trackpoint in tree.findall(".//{" + TCD_NS + "}Trackpoint[{" + TCD_NS + "}HeartRateBpm]"):
            iso_time = trackpoint.find("{" + TCD_NS + "}Time").text
            heartratebpm = trackpoint.find("{" + TCD_NS + "}HeartRateBpm/{" + TCD_NS + "}Value").text
            self._heartrates[iso_time] = heartratebpm


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

        if iso_time in self._heartrates:
            bpm = self._heartrates[iso_time]
            self._add_heart_rate(bpm, trackpoint)
        elif len(self._heartrates) > 0:
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

    def _update_calories(self):
        calphs = {}
        elapsed_seconds = 0
        for second, calph in self._caloriesPerHour.items():
            calphs[calph] = calphs.get(calph, 0) + second - elapsed_seconds
            elapsed_seconds = second
        calph_mean = harmonic_mean(calphs.keys(), weights=calphs.values())
        total_time_hours = int(self._totalTimeSeconds.text)/3600
        self._calories.text = str(round(calph_mean * total_time_hours))

    def write(self, f):
        self._update_calories()
        ET.indent(self._root, space="\t", level=0)
        ET.ElementTree(self._root).write(f, encoding='utf-8', method="xml",xml_declaration=True)

    def tostring(self):
        self._update_calories()
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
    def _add_heart_rate(bpm, trackpoint):
        heartratebpm = ET.SubElement(trackpoint, "HeartRateBpm")
        heartratebpm_value = ET.SubElement(heartratebpm, "Value")
        heartratebpm_value.text = bpm
