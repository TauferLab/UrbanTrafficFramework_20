import csv
import numpy as np
from matplotlib.axes import Axes

from matplotlib.colors import Normalize, ListedColormap
from matplotlib import pyplot as plt, cm
# noinspection PyProtectedMember
from numpy.random._generator import default_rng

from src.maps.plot_heatmap import html_to_rgba, get_color, N_COLORS
from src.maps.plot_roads import plot_roads
from src.maps.plot_vehicle_mappings import load_buildings, fences
from src.support.emissions import EmissionsSnapshot
from src.support.heatmap import X_MIN, X_MAX, Y_MIN, Y_MAX, comp_all
from src.support.roadnet import RoadNetwork
from sys import argv, exit, stderr

LOG_SCALING = False
SEED = 5123125123

Z_ORDER_ROAD, Z_ORDER_BUILDING, Z_ORDER_MARKER, Z_ORDER_HEAT = range(0, 4)

COLOR_BASE_1 = [html_to_rgba(color) for color in [
    '#ffffffff',
    '#080808ff'
]]
COLOR_BASE_2 = [html_to_rgba(color) for color in [
    '#f20d0d00',
    '#f2460dff',
    '#f2800dff',
    '#f4e025ff'
]]

HEAT_CM_1 = ListedColormap([get_color(k / N_COLORS, COLOR_BASE_1) for k in range(0, N_COLORS)])
HEAT_CM_1_ALPHA = ListedColormap([get_color(k / N_COLORS, COLOR_BASE_1, True) for k in range(0, N_COLORS)])
HEAT_CM_2 = ListedColormap([get_color(k / N_COLORS, COLOR_BASE_2) for k in range(0, N_COLORS)])
HEAT_CM_2_ALPHA = ListedColormap([get_color(k / N_COLORS, COLOR_BASE_2, True) for k in range(0, N_COLORS)])


def main():
    if len(argv) < 6:
        stderr.write(
            f"USAGE: {argv[0]} [path to road network GEOJSON file] [path to simplified building data] "
            f"[path to mappings file] [path to emissions file] [output path]"
        )
        exit(1)

    with open(argv[1], 'r', encoding='utf-8') as file:
        network = RoadNetwork(file)

    buildings = load_buildings(argv[2], z_order=Z_ORDER_BUILDING)

    with open(argv[3], 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
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
    bldg_norm = Normalize(0, cf2, clip=True)

    # Set up figure and axes:
    fig = plt.figure()
    ax: Axes = fig.add_subplot()

    plot_roads(ax, network, color_roads=False, plot_nodes=False, z_order=Z_ORDER_ROAD,
               alpha=0.25, default_road_color='#FFFFFF')

    for bldg in buildings.values():
        edge_alpha = 0.75
        alpha = 0.5

        if bldg["count"] <= 0:
            bldg["color"] = (0, 0, 0, 0)
            edge_alpha = 0.5
        else:
            if LOG_SCALING:
                count = np.log(bldg["count"])
            else:
                count = bldg["count"]

            bldg["color"] = HEAT_CM_1(bldg_norm(count))

        patch = bldg["poly"]
        patch.set_edgecolor((0, 0, 0, edge_alpha))
        patch.set_facecolor(bldg["color"])
        patch.set_fill(True)
        ax.add_patch(patch)

    vids = np.fromiter(mappings.keys(), int, len(mappings))
    n = min(len(mappings), 2500)
    rng = default_rng(SEED)

    sample = rng.choice(vids, size=n, replace=False)

    with open(argv[4], 'r', encoding='utf-8') as file:
        emissions = EmissionsSnapshot.load(file)
    hmap, link_cells, max_value = comp_all(network, emissions)
    em_norm = Normalize(0, max_value, clip=True)
    ax.imshow(hmap, cmap=HEAT_CM_2_ALPHA, zorder=Z_ORDER_HEAT, extent=(X_MIN, X_MAX, Y_MIN, Y_MAX))

    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)

    ax.set_xticks([])
    ax.set_yticks([])
    fig.colorbar(cm.ScalarMappable(norm=bldg_norm, cmap=HEAT_CM_1), label="Mapped Vehicle Count")
    fig.colorbar(cm.ScalarMappable(norm=em_norm, cmap=HEAT_CM_2), label="Emissions Quantity (MMBtu)")
    plt.savefig(argv[5])
    plt.show()


if __name__ == '__main__':
    main()
