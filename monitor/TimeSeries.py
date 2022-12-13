from collections import OrderedDict
from statistics import harmonic_mean


class TimeSeries(object):

    __ordered_time_series: OrderedDict

    def __init__(self, time_series: dict[int, any]) -> None:
        self.__ordered_time_series = OrderedDict(sorted(time_series.items()))

    def get_max(self):
        return max(self.__ordered_time_series.values())

    def get_harmonic_mean(self):
        distribution = {}
        elapsed_seconds = 0
        for second, value in self.__ordered_time_series.items():
            if value > 0:
                distribution[value] = distribution.get(value, 0) + second - elapsed_seconds
            elapsed_seconds = second
        return harmonic_mean(distribution.keys(), weights=distribution.values())
