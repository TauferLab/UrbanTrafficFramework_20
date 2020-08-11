import sys
import numpy as np
from numpy.random import default_rng
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from src.maps.plot_roads import plot_roads
from src.support.roadnet import RoadNetwork
from src.support.simsio import Snapshot, Trace


SAMPLE_PROPORTION = 0.01
SEED = 1592417421


def plot_trace(trace: Trace, color) -> Line2D:
    xs = np.zeros(len(trace))
    ys = np.zeros(len(trace))

    prev = None
    for i, frame in enumerate(trace):
        if prev is not None:
            ds = np.hypot(frame.x - prev.x, frame.y - prev.y)
            dt = (frame.time - prev.time) * 30
            if (ds / dt) > 37.616:
                return None

        xs[i] = frame.x
        ys[i] = frame.y
        prev = frame

    return Line2D(xs, ys, linestyle="-", marker=".", color=color)


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to road network GeoJSON file] [path to snapshot data]\n"
        )
        sys.exit(1)

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot(aspect="equal")

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        network = RoadNetwork(f)
    plot_roads(ax, network, False, False)

    # Load and render traces:
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        snapshot = Snapshot.load(f, ordered=False)

    rng = default_rng(SEED)
    i = 0
    for trace in snapshot.iter_traces():
        if rng.random() >= SAMPLE_PROPORTION:
            continue

        line = plot_trace(trace, rng.random(3))
        if line is None:
            continue

        ax.add_line(line)
        i += 1

        if i % 10 == 0:
            sys.stderr.write("Plotted {} traces...\n".format(i))
            sys.stderr.flush()

    ax.autoscale_view()

    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Vehicle Traces")

    plt.show()


if __name__ == "__main__":
    main()
