from monitor.Capture import Capture
from monitor.Monitor import Monitor


class Recorder(Monitor):

    def __init__(self, port) -> None:
        super().__init__(port)
        self.__session_file = None
        self.__session_distance = None

    def on_connected(self):
        super().on_connected()

    def on_data(self, data, milliseconds):
        super().on_data(data, milliseconds)
        if data[:1] == "A":
            capture = Capture(milliseconds, data)
            self.__update_session_file_if_needed(capture.distance, milliseconds)
            self.__session_file.write("{} {}\n".format(milliseconds, data))

    def on_disconnected(self):
        super().on_disconnected()
        self.__close_session_file()

    def __update_session_file_if_needed(self, distance, milliseconds):
        if self.__is_new_file_required(distance):
            self.__close_session_file()
            filename = str(milliseconds) + ".txt"
            print("Starting new session: {}".format(filename))
            self.__session_file = open(filename, "w")
        self.__session_distance = distance

    def __is_new_file_required(self, distance):
        if distance and self.__session_distance:
            if distance < self.__session_distance:
                return True
        return self.__session_file is None

    def __close_session_file(self):
        if self.__session_file:
            print("Closing file.")
            self.__session_file.close()
