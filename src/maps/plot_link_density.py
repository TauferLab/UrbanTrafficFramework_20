import sys
import numpy as np
from collections import Counter
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

from src.support.roadnet import RoadNetwork, Link
from src.support.simsio import Snapshot


def plot_road(road: Link, color: np.ndarray) -> Line2D:
    xs = [p[0] for p in road.points]
    ys = [p[1] for p in road.points]
    return Line2D(xs, ys, linestyle="-", marker=None, color=color, linewidth=1.5)


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
    ax = fig.add_subplot(121, aspect="equal")

    # Load traces and count # of frames per link:
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        snapshot = Snapshot.load(f, ordered=False)
    link_counts = Counter(frame.link for frame in snapshot.iter_time())

    # print("most common links: ", link_counts.most_common(10))

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        network = RoadNetwork(f)

    counts = np.zeros(len(network.links))
    for road in network.links:
        counts[road.id] = link_counts.get(road.id, 0)

    # Filter outliers in count data:
    q1 = np.percentile(counts, 25)
    q3 = np.percentile(counts, 75)
    iqr = q3 - q1
    f1 = q1 - (1.5 * iqr)
    f2 = q3 + (1.5 * iqr)

    plotted = {}
    for road in network.links:
        v = counts[road.id]
        if v < f1 or v > f2:
            continue
        plotted[road.id] = v
    
    # Plot roads:
    cmap = plt.get_cmap("viridis")
    nm = Normalize()
    nm.autoscale([v for v in plotted.values()])

    for road in network.links:
        if road.id in plotted:
            color = cmap(nm(plotted[road.id]))
        else:
            color = (0, 0, 0, 0)
        ax.add_line(plot_road(road, color))
    ax.autoscale_view()

    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Link Density")

    print("nonzero links: ", np.count_nonzero(counts))

    ax2 = fig.add_subplot(122)
    ax2.hist(counts, bins="auto")
    ax2.axvline(f1, linestyle='--', color='k')
    ax2.axvline(f2, linestyle='--', color='k')
    ax2.axvline(q1, linestyle='--', color='r')
    ax2.axvline(q3, linestyle='--', color='r')
    ax2.set_xlabel("Density")
    ax2.set_ylabel("Frequency")
    ax2.set_title("Densities")

    plt.show()


if __name__ == "__main__":
    main()
