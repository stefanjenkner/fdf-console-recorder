#!/usr/bin/env python
import argparse

from monitor.Recorder import Recorder

DEFAULT_PORT = '/dev/ttyUSB0'


def main():
    parser = argparse.ArgumentParser(prog="FDF Console recorder", description="Record console session")

    parser.add_argument("--port", "-p", metavar="PORT", required=False, default=DEFAULT_PORT,
                        help=f"Serial port to use for recording, defaults to {DEFAULT_PORT}")

    args = parser.parse_args()
    recorder = Recorder(args.port)
    recorder.start()


if __name__ == '__main__':
    main()
