import copy
import csv
import numpy as np
from typing import Tuple
from matplotlib import pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, Colormap
from matplotlib.collections import PolyCollection
import sys

from ..support.buildings import BuildingCollection
from ..support.roadnet import RoadNetwork
from .roads import plot_roads


def plot_buildings(
    buildings: BuildingCollection,
    normalized_count: bool,
    bbox_sw: np.ndarray,
    bbox_ne: np.ndarray,
    cmap: Colormap,
    zorder=None,
) -> Tuple[PolyCollection, PolyCollection, ScalarMappable]:
    """
    Plot a BuildingCollection using matplotlib.

    Returns a tuple containing two PolyCollection objects that can be used to
    draw buildings onto a matplotlib Axes object, as well as a ScalarMappable
    that can be used to draw a colorbar if desired.

    The first returned PolyCollection contains buildings with nonzero counts,
    while the second contains buildings with zero counts.
    """

    map_bound_west = bbox_sw[0]
    map_bound_east = bbox_ne[0]
    map_bound_south = bbox_sw[1]
    map_bound_north = bbox_ne[1]

    nonzero_verts = []
    counts = []
    zero_verts = []

    for building in buildings:
        if (
            building.bbox_east > map_bound_east
            or building.bbox_west < map_bound_west
            or building.bbox_north > map_bound_north
            or building.bbox_south < map_bound_south
        ):
            continue

        if building.count is not None:
            nonzero_verts.append(building.bbox_pts)
            if normalized_count:
                counts.append(building.norm_count)
            else:
                counts.append(building.count)
        else:
            zero_verts.append(building.bbox_pts)

    # Tukey's fences:
    q1 = np.percentile(counts, 25)
    q3 = np.percentile(counts, 75)
    iqr = q3 - q1
    f2 = q3 + (1.5 * iqr)
    norm = Normalize(0, f2)
    colors = cmap(norm(counts))

    nonzero_coll = PolyCollection(
        nonzero_verts,
        edgecolors=[(0, 0, 0, 1)],
        facecolors=colors,
        zorder=zorder,
        linewidths=0.50,
    )

    zero_coll = PolyCollection(
        zero_verts,
        edgecolors=[(0, 0, 0, 1)],
        facecolors=[(0, 0, 0, 0)],
        zorder=zorder,
        linewidths=0.50,
    )

    return (nonzero_coll, zero_coll, ScalarMappable(norm=norm, cmap=cmap))


def _main():
    if len(sys.argv) < 4 or sys.argv[3] not in ["raw", "normalized"]:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to complete buildings CSV] [path to building counts CSV] ['raw' | 'normalized'] [optional path to road network GeoJSON file]\n"
        )
        sys.exit(1)

    # load all buildings:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        all_bldgs = BuildingCollection.load_csv(f)

    # load counts data:
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        counts = BuildingCollection.load_csv(f)

    merged = all_bldgs.merge(counts)
    bbox_ne = np.array([np.Inf, np.Inf])
    bbox_sw = np.array([-np.Inf, -np.Inf])

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot(aspect="equal")

    # load roads if passed:
    if len(sys.argv) >= 5:
        with open(sys.argv[4], "r", encoding="utf-8") as f:
            roads = RoadNetwork(f)

        roads_coll = plot_roads(
            roads,
            z_order=3,
            color_roads=False,
            default_road_color=(0.66, 0.66, 0.66, 1),
        )
        bbox_ne, bbox_sw = roads.bbox()

        ax.add_collection(roads_coll)

    cmap = copy.copy(plt.get_cmap("viridis"))
    cmap.set_over(cmap(1.0))

    plot_norm_count = sys.argv[3].lower() == "normalized"
    nonzero_bldgs, zero_bldgs, scalar_map = plot_buildings(
        merged, plot_norm_count, bbox_sw, bbox_ne, cmap, 2
    )

    if plot_norm_count:
        label = "Normalized Vehicle Count"
    else:
        label = "Mapped Vehicle Count"

    ax.add_collection(nonzero_bldgs)
    ax.add_collection(zero_bldgs)
    ax.autoscale_view()

    fig.colorbar(scalar_map, label=label, ax=ax, extend="max")

    ax.set_xticks([])
    ax.set_yticks([])

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    _main()
