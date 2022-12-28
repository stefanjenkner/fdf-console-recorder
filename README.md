# FDF Console recorder

Record rowing sessions from First Degree Fitness water rowers and generate TCX files.

Tested with First Degree Fitness NEON plus water rower which comes with the (basic)
FDF Console and a serial interface.

## Usage

### 1. Record session

Connect the FDF console via USB and record a session by running:
```
recorder.py --port /dev/ttyS0
```
This will generate a TXT file with a timestamp, e.g.: `1670609153225.txt`. Stop recording with Ctrl-C.

### 2. Export session to TCX

Convert the recording to TCX by running:

```
./export.py 1671385156654.txt 1670609153225.tcx
```

In order to load heart rate info from an external source, e.g. FIT file:

```
./export.py --fit-input 1670609153225_watch.fit 1670609153225.txt 1670609153225.tcx
```

In order to load heart rate info from a TCX file:

```
./export.py --fit-input 1670609153225_watch.tcx 1670609153225.txt 1670609153225.tcx
```

## Notes

- no support yet to read HR info from FDF console directly (requires additional hardware)
- BPM information from exteral files (TCX and FIT) are interpolated
