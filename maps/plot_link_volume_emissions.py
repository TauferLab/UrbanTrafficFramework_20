import sys
from typing import Tuple
import numpy as np
from collections import Counter
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

from support.roadnet import RoadNetwork, Link
from support import linkvolio
from support.emissions import EmissionsSnapshot


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to road network GeoJSON file] [path to link volume data] [path to emissions snapshot]\n"
        )
        sys.exit(1)

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot(111)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        network = RoadNetwork(f)

    # Load traces and count # of frames per link:
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        volumes = linkvolio.link_volumes(f)

    # Load emissions snapshot data:
    with open(sys.argv[3], "r", encoding="utf-8") as f:
        snapshot = EmissionsSnapshot.load(f)

    xs = []
    ys = []

    for road in network.links:
        if road.id in volumes and road.id in snapshot.data:
            xs.append(volumes[road.id].link_vol)
            ys.append(snapshot.data[road.id].quantity)

    ax.plot(xs, ys, '.')
    ax.set_title("Recorded Link Volume vs. Emissions Quantity")
    ax.set_xlabel("Link Volume (vehicles / hour)")
    ax.set_ylabel("Emissions Quantity (MMBtu)")

    plt.show()


if __name__ == "__main__":
    main()
