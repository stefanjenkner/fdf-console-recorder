import time
import serial

from monitor import Capture

def main():

    sessionFile = None
    sessionDistance = None

    console = serial.Serial()
    console.port = '/dev/ttyUSB0'
    console.baudrate=9600
    console.bytesize=serial.EIGHTBITS
    console.parity=serial.PARITY_NONE
    console.stopbits=serial.STOPBITS_ONE
    console.timeout=1

    while True:

        if not console.is_open:
            try:
                console.open()
                console.write('C\n'.encode('utf-8'))
                out = console.readline()
                print("Connected.")

            except:
                print("Error opening connection")
                if sessionFile:
                    sessionFile.close()
                exit()

        try:

            milliseconds = round(time.time()*1000)
            time.sleep(500/1000)

            if sessionFile is None:
                sessionFile = open_new_file(milliseconds)

            out = ""
            out_bytes = console.readline()
            print(out_bytes)
            if out_bytes != '':
                out = out_bytes.decode('utf-8')
                out = out.strip()
            if out[:1] == "A":
                capture = Capture(out) 
                
                if capture.distance and sessionDistance:
                    if capture.distance < sessionDistance:
                        sessionFile.close()
                        sessionFile = open_new_file(milliseconds)
            
                sessionDistance = capture.distance
                sessionFile.write("{} {}\n".format(milliseconds, out))
                print("{} {}".format(milliseconds, out))

        except KeyboardInterrupt:
            print("Interrupted.")
            if sessionFile is not None:
                print("Closing file.")
                sessionFile.close()
            if console.is_open:
                print("Closing connection.")
                console.write('D\n'.encode('utf-8'))
                console.close()
            exit()


def open_new_file(milliseconds):
    """
    """
    filename = str(milliseconds) + ".txt"
    print("Starting new session: {}".format(filename))
    return open(filename, "w")   

        

if __name__ == '__main__':
    main()

