import time

import serial


class Monitor(object):

    def __init__(self, port) -> None:
        self.__console = serial.Serial()
        self.__console.port = port
        self.__console.baudrate = 9600
        self.__console.bytesize = serial.EIGHTBITS
        self.__console.parity = serial.PARITY_NONE
        self.__console.stopbits = serial.STOPBITS_ONE
        self.__console.timeout = 1

    def start(self) -> None:

        while True:

            if not self.__console.is_open:
                try:
                    self.__console.open()
                    self.__console.write('C\n'.encode('utf-8'))
                    self.__console.readline()
                    self.on_connected()

                except:
                    print(f"Error opening connection via port {self.__console.port}")
                    self.on_disconnected()
                    exit()

            try:
                time.sleep(500 / 1000)
                data = self.__wait_for_data()
                milliseconds = round(time.time() * 1000)
                self.on_data(data, milliseconds)

            except KeyboardInterrupt:
                print("Interrupted.")
                self.__disconnect()
                exit()

    def on_connected(self):
        print("Connected.")

    def on_data(self, data, milliseconds):
        print(f"> {milliseconds} {data}")

    def on_disconnected(self):
        print("Disconnected.")

    def __wait_for_data(self):
        data = ""
        data_bytes = self.__console.readline()
        if data_bytes != '':
            data = data_bytes.decode("utf-8")
            data = data.strip()
        return data

    def __disconnect(self):
        if self.__console.is_open:
            print("Closing connection.")
            self.__console.write('D\n'.encode('utf-8'))
            self.__console.close()
        self.on_disconnected()
