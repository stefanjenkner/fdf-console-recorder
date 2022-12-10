import datetime
import xml.etree.ElementTree as ET
from io import BytesIO

from monitor import Capture

XSI = "http://www.w3.org/2001/XMLSchema-instance"
TCD = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
AE = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"

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
    _extensions = None

    def __init__(self):
        builder = ET.TreeBuilder()
        ET.register_namespace("", TCD)
        ET.register_namespace("xsi", XSI)
        ET.register_namespace("ae", AE)
        builder.start("{"+TCD+"}TrainingCenterDatabase", {})
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
        self._extensions = builder.start("Extensions", {})
        self._root = builder.close()
        lx = ET.SubElement(self._extensions, "{"+AE+"}LX")
        self._maxWatts = ET.SubElement(lx, "{"+AE+"}MaxWatts")


    def add_trackpoint(self, capture:Capture):
        """

        :return:
        """
        #
        if not self._isInitialized:
            self._init(capture)

        totalTimeSeconds = capture.totalMinutes*60 + capture.totalSeconds
        totalTimeHours = totalTimeSeconds/3600
        self._totalTimeSeconds.text = str(totalTimeSeconds)
        self._distanceMeters.text = str(capture.distance)
        # fix
        self._calories.text = str(round(capture.caloriesPerHour*totalTimeHours))

        trackpoint = ET.SubElement(self._track, "Trackpoint")
        time = ET.SubElement(trackpoint, "Time")
        time.text = self._get_formated_time(capture)
        distance_meters = ET.SubElement(trackpoint, "DistanceMeters")
        distance_meters.text = str(capture.distance)
        cadence = ET.SubElement(trackpoint, "Cadence")
        cadence.text = str(capture.strokesPerMinute)
        extensions = ET.SubElement(trackpoint, "Extensions")
        tpx = ET.SubElement(extensions, "{"+AE+"}TPX")
        watts = ET.SubElement(tpx, "{"+AE+"}Watts")
        watts.text = str(capture.watt)

        if not self._maxWatts.text:
            self._maxWatts.text = str(capture.watt)
        else:
            self._maxWatts.text = str(max(int(self._maxWatts.text), capture.watt))

    def _init(self, capture: Capture):
        self._intensity.text = "Active"
        self._triggerMethod.text = "Manual"
        self._id.text = self._get_formated_time(capture)
        self._lap.attrib["StartTime"] = self._get_formated_time(capture)
        self._isInitialized = True

    def write(self, f):
        ET.indent(self._root, space="\t", level=0)
        ET.ElementTree(self._root).write(f, encoding='utf-8', method="xml",xml_declaration=True)

    def tostring(self):
        result = BytesIO()
        ET.indent(self._root, space="\t", level=0)
        ET.ElementTree(self._root).write(result, encoding='utf-8', method="xml",xml_declaration=True)
        return result.getvalue().decode()

    @staticmethod
    def _get_formated_time(capture):
        return capture.time.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _add_empty(builder, tag):
        builder.start(tag, {})
        return builder.end(tag)
