import sys
from typing import List
import numpy as np
from matplotlib import pyplot as plt

from src.support.simsio import Snapshot, Trace

SAMPLE_PROPORTION = 0.01
SEED = 1592417421


def calculate_speed(trace: Trace) -> List[float]:
    speeds = []

    prev = None
    for frame in trace:
        if prev is not None:
            ds = np.hypot(frame.x - prev.x, frame.y - prev.y)
            dt = (frame.time - prev.time) * 30
            speeds.append(ds / dt)
        prev = frame

    return speeds


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to snapshot data]\n"
        )
        sys.exit(1)

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot()

    # Load traces:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        snapshot = Snapshot.load(f, ordered=False)

    speeds = []
    for i, trace in enumerate(snapshot.iter_traces()):
        speeds.extend(calculate_speed(trace))
        if i % 1000 == 0:
            sys.stderr.write("Calculated {} speeds...\n".format(i))
            sys.stderr.flush()
    speeds = np.array(speeds)
    nonzero_speeds = speeds[speeds > 0]

    q1 = np.percentile(nonzero_speeds, 25)
    q3 = np.percentile(nonzero_speeds, 75)
    iqr = q3 - q1
    f1 = q1 - (1.5 * iqr)
    f2 = q3 + (1.5 * iqr)
    filtered = speeds[(speeds >= f1) & (speeds <= f2)]

    print("f1: {:.3f}".format(f1))
    print("f2: {:.3f}".format(f2))
    print("q1: {:.3f}".format(q1))
    print("q3: {:.3f}".format(q3))

    ax.hist(filtered, bins="auto")
    ax.axvline(f1, linestyle='--', color='k')
    ax.axvline(f2, linestyle='--', color='k')
    ax.axvline(q1, linestyle='--', color='r')
    ax.axvline(q3, linestyle='--', color='r')
    ax.set_xlabel("Vehicle Speed (m/s)")
    ax.set_ylabel("Frequency")
    ax.set_title("Vehicle Trace Speeds")
    plt.show()


if __name__ == "__main__":
    main()
