#!/usr/bin/env python

import argparse

from console.Capture import Capture
from console.Export import Export


def main():
    parser = argparse.ArgumentParser(prog='FDF Console record exporter', description='Convert recording to TCX')

    parser.add_argument('record_filename', metavar='TXT_INPUT',
                        help='recording in TXT format')
    parser.add_argument('output_filename', metavar='TCX_OUTPUT',
                        help='output file in TCX format')
    parser.add_argument('--fit-input', metavar='FIT_INPUT', required=False,
                        help='secondary source for hear rate data in FIT format')
    parser.add_argument('--tcx-input', metavar='TCX_INPUT', required=False,
                        help='secondary source for hear rate data in TCX format')
    args = parser.parse_args()

    export = Export()

    if args.fit_input:
        export.load_heart_rate_from_fit(args.fit_input)
    elif args.tcx_input:
        export.load_heart_rate_from_tcx(args.tcx_input)

    with open(args.record_filename, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            (milliseconds, data) = line.split(" ")
            export.add_track_point(Capture(int(milliseconds), data))

    with open(args.output_filename, 'wb') as f:
        export.write(f)


if __name__ == "__main__":
    main()
