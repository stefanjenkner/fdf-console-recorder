import time

import serial

from monitor.Capture import Capture


class Recorder(object):

    def __init__(self, port) -> None:
        self.__console = serial.Serial()
        self.__console.port = port
        self.__console.baudrate = 9600
        self.__console.bytesize = serial.EIGHTBITS
        self.__console.parity = serial.PARITY_NONE
        self.__console.stopbits = serial.STOPBITS_ONE
        self.__console.timeout = 1
        self.__session_file = None
        self.__session_distance = None

    def start(self) -> None:

        while True:

            if not self.__console.is_open:
                try:
                    self.__console.open()
                    self.__console.write('C\n'.encode('utf-8'))
                    self.__console.readline()
                    print("Connected.")

                except:
                    print("Error opening connection")
                    self.__close_session_file()
                    exit()

            try:
                time.sleep(500 / 1000)
                out = self.__readline()
                milliseconds = round(time.time() * 1000)
                print("{} {}".format(milliseconds, out))

                if out[:1] == "A":
                    capture = Capture(milliseconds, out)
                    self.__update_session_file_if_needed(capture.distance, milliseconds)
                    self.__session_file.write("{} {}\n".format(milliseconds, out))

            except KeyboardInterrupt:
                print("Interrupted.")
                self.__close_session_file()
                self.__disconnect()
                exit()

    def __readline(self):
        out = ""
        out_bytes = self.__console.readline()
        if out_bytes != '':
            out = out_bytes.decode('utf-8')
            out = out.strip()
        return out

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

    def __disconnect(self):
        if self.__console.is_open:
            print("Closing connection.")
            self.__console.write('D\n'.encode('utf-8'))
            self.__console.close()
