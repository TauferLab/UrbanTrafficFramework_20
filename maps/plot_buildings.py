import sys
import json
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from matplotlib.ticker import MultipleLocator

from support.utm import convert_to_utm

# All of the coordinates in the building footprints data are in UTM Zone 16,
# with a central meridian of 87W.
CENT_LON = -87


def plot_buildings(source_file, bbox_x=None, bbox_y=None):
    with open(source_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    n_buildings = len(data["features"])
    print("Loaded {} buildings".format(n_buildings))

    patches = []
    for i, feature in enumerate(data["features"]):
        if i % 1000 == 0:
            print("Proccessing buildings: {:.1%}".format((i + 1) / n_buildings))

        assert feature["type"] == "Feature"
        geom = feature["geometry"]

        # we only support plotting basic Polygons for now
        assert geom["type"] == "Polygon"
        rings = geom["coordinates"]

        assert len(rings) == 1
        ext = rings[0]

        # Create a NumPy array of shape Nx2, where N is the number of
        # points in the polygon
        seq = map(lambda coords: convert_to_utm(coords[1], coords[0], CENT_LON), ext)
        stacked = np.stack(tuple(seq))

        # Clip rendered buildings if a bbox was provided
        if bbox_x is not None:
            if np.min(stacked[:, 0]) < bbox_x[0] or np.max(stacked[:, 0]) > bbox_x[1]:
                continue

        if bbox_y is not None:
            if np.min(stacked[:, 1]) < bbox_y[0] or np.max(stacked[:, 1]) > bbox_y[1]:
                continue
        
        patches.append(Polygon(stacked, True))

    p = PatchCollection(patches, alpha=0.4)

    # Randomly colorize each building:
    colors = 100 * np.random.rand(len(patches))
    p.set_array(np.array(colors))

    return p


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(
            "USAGE: " + sys.argv[0] + " [path to building footprints GeoJSON data]\n"
        )
        sys.exit(1)

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot(aspect="equal")

    ax.add_collection(plot_buildings(sys.argv[1]))
    ax.autoscale_view()

    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Building Footprints")

    plt.show()


if __name__ == "__main__":
    main()
