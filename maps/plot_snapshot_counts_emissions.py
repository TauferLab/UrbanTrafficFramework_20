import sys
from typing import Tuple
import numpy as np
from collections import Counter
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

from support.roadnet import RoadNetwork, Link
from support.simsio import Snapshot
from support.emissions import EmissionsSnapshot


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to road network GeoJSON file] [path to snapshot data] [path to emissions snapshot]\n"
        )
        sys.exit(1)

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot(111)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        network = RoadNetwork(f)

    # Load traces and count # of frames per link:
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        snapshot = Snapshot.load(f, ordered=False)
    link_counts = {}

    for road in network.links:
        link_counts[road.id] = set()

    for frame in snapshot.iter_time():
        link_counts[frame.link].add(frame.vid)

    for road in network.links:
        link_counts[road.id] = len(link_counts[road.id])

    # Load emissions snapshot data:
    with open(sys.argv[3], "r", encoding="utf-8") as f:
        snapshot = EmissionsSnapshot.load(f)

    xs = []
    ys = []

    for road in network.links:
        if road.id in link_counts and road.id in snapshot.data:
            xs.append(link_counts[road.id])
            ys.append(snapshot.data[road.id].quantity)

    ax.plot(xs, ys, '.')
    ax.set_title("Recorded Snapshot Vehicle Counts vs. Emissions Quantities")
    ax.set_xlabel("Derived Link Volume (vehicles)")
    ax.set_ylabel("Emissions Quantity (MMBtu)")

    plt.show()


if __name__ == "__main__":
    main()
