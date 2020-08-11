import sys
from matplotlib import pyplot as plt

from src.support.roadnet import RoadNetwork
from src.support.simsio import Snapshot
from src.support import linkvolio


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to road network GeoJSON file] [path to snapshot data] [path to link volume data]\n"
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

    # Load link volume snapshot data:
    with open(sys.argv[3], "r", encoding="utf-8") as f:
        vols = linkvolio.link_volumes(f)

    xs = []
    ys = []

    for road in network.links:
        if road.id in link_counts and road.id in vols:
            ys.append(link_counts[road.id])
            xs.append(vols[road.id].link_vol)

    ax.plot(xs, ys, '.')
    ax.set_ylabel("Vehicles on Link (Snapshot Data)")
    ax.set_xlabel("Vehicles on Link (Link Volume Data)")
    ax.set_title("Link Volume Correlation")

    plt.show()


if __name__ == "__main__":
    main()
