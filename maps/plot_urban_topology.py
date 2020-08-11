import os.path as osp
import sys
import numpy as np
from matplotlib import pyplot as plt

from plot_buildings import plot_buildings
from plot_roads import plot_roads

def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "USAGE: " + sys.argv[0] + " [path to buildings GeoJSON file] [path to road network GeoJSON file]\n"
        )
        sys.exit(1)

    # Set up figure, axes:
    fig = plt.figure()
    ax = fig.add_subplot(aspect="equal")

    # Load and render road network first, so we can determine our region of
    # interest:
    road_xs, road_ys = plot_roads(ax, sys.argv[2])
    bbox_x = (np.min(road_xs), np.max(road_xs))
    bbox_y = (np.min(road_ys), np.max(road_ys))

    # Render buildings within the area encompassed by the road network:
    ax.add_collection(plot_buildings(sys.argv[1], bbox_x, bbox_y))
    ax.autoscale_view()

    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Urban Topology")

    plt.show()


if __name__ == "__main__":
    main()
