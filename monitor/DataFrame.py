import datetime

import pandas as pd


class DataFrame(object):

    __df: pd.DataFrame

    def __init__(self, start: datetime.datetime, end: datetime.datetime) -> None:
        index = pd.date_range(start=start, end=end, inclusive='both', freq='s')
        self.__df = pd.DataFrame(index=index, columns=[])

    def load_from_dict(self, data: dict[datetime.datetime, any], column_name):
        external = pd.DataFrame.from_dict(data, orient='index', columns=[column_name])
        self.__df = pd.concat([(self.__df), external], join='outer', axis=1)

    def interpolate(self, existing_column, new_column, method='nearest'):
        self.__df[new_column] = self.__df[existing_column].interpolate(method=method)

    def get(self, at_time: datetime.datetime, column):
        at_time_round_to_second = pd.to_datetime(at_time).round('S')
        try:
            return self.__df.at_time(at_time_round_to_second)[column].iloc[0]
        except IndexError:
            pass
        return None

    def mean(self, start, end, column):
        start__round = pd.to_datetime(start).round('S')
        end__round = pd.to_datetime(end).round('S')
        return self.__df[start__round:end__round].mean(axis=0)[column]

    def max(self, start, end, column):
        start__round = pd.to_datetime(start).round('S')
        end__round = pd.to_datetime(end).round('S')
        return self.__df[start__round:end__round].max(axis=0)[column]