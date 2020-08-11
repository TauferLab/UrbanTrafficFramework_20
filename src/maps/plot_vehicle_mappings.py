import csv
import sys
from typing import Tuple

import numpy as np
from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from numpy.random import default_rng

from src.maps.plot_heatmap import HEAT_CM_1
from src.maps.plot_roads import plot_roads
from src.support.roadnet import RoadNetwork

# All of the coordinates in the building footprints data are in UTM Zone 16,
# with a central meridian of 87W.
CENT_LON = -87
SEED = 5123125123
LOG_SCALING = False


def load_buildings(source_file, z_order=None, bbox_x=None, bbox_y=None):
    with open(source_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)

        next(reader)

        buildings = {}
        for row in reader:
            bldg_id = int(row[0])
            center = np.array([float(row[1]), float(row[2])])
            
            try:
                count = int(row[8])
            except (IndexError, ValueError):
                count = 0

            east = float(row[4])
            west = float(row[5])
            north = float(row[6])
            south = float(row[7])

            pts = np.array(
                [[east, north], [west, north], [west, south], [east, south]]
            )

            buildings[bldg_id] = {
                "center": center,
                "poly": Polygon(pts, True, fill=False, zorder=z_order),
                "count": count,
            }

        return buildings


def fences(values: np.ndarray) -> Tuple[float, float, float, float]:
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    f1 = q1 - (3 * iqr)
    f2 = q3 + (3 * iqr)

    return q1, q3, f1, f2


def main():
    if len(sys.argv) < 4:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to simplified building data] [path to mappings] [road network]\n"
        )
        sys.exit(1)

    buildings = load_buildings(sys.argv[1])

    with open(sys.argv[3], 'r', encoding='utf-8') as file:
        network = RoadNetwork(file)

    with open(sys.argv[2], "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)

        mappings = {}
        for row in reader:
            vehicle = int(row[0])
            bldg = int(row[4])
            mapped_count = int(row[8])

            buildings[bldg]["count"] = mapped_count
            mappings[vehicle] = {
                "building": bldg,
                "x": float(row[2]),
                "y": float(row[3]),
                "distance": float(row[7])
            }

    counts = np.fromiter(filter(lambda x: x > 0, map(lambda b: b["count"], buildings.values())), float)
    if LOG_SCALING:
        counts = np.log(counts)

    cq1, cq3, cf1, cf2 = fences(counts)
    norm = Normalize(0, cf2, clip=True)

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot(aspect="equal")

    plot_roads(ax, network, color_roads=False, plot_nodes=False, alpha=0.70, default_road_color='#FFFFFF')

    for bldg in buildings.values():
        edge_alpha = 1.0
        alpha = 0.8

        if bldg["count"] <= 0:
            bldg["color"] = (0, 0, 0, 0)
            edge_alpha = 0.5
        else:
            if LOG_SCALING:
                count = np.log(bldg["count"])
            else:
                count = bldg["count"]

            bldg["color"] = HEAT_CM_1(norm(count), alpha=alpha)

        patch = bldg["poly"]
        patch.set_edgecolor((0, 0, 0, edge_alpha))
        patch.set_facecolor(bldg["color"])
        patch.set_fill(True)
        ax.add_patch(patch)

    vids = np.fromiter(mappings.keys(), int, len(mappings))
    n = min(len(mappings), 2500)
    rng = default_rng(SEED)

    sample = rng.choice(vids, size=n, replace=False)

    for vid in sample:
        frame = mappings[vid]
        bldg = buildings[frame["building"]]

        xs = [frame["x"], bldg["center"][0]]
        ys = [frame["y"], bldg["center"][1]]
        ax.add_line(Line2D(xs, ys, linestyle="-", marker='.', markevery=[0], linewidth=1, color=(0, 0, 0, 0.5)))

    ax.autoscale_view()

    ax.set_facecolor((0.50, 0.50, 0.50, 1.0))
    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Vehicle Mapping Density, 10 AM")
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap=HEAT_CM_1))

    plt.show()


if __name__ == "__main__":
    main()
