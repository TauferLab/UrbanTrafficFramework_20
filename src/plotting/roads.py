import sys
from typing import Tuple, List
from matplotlib import pyplot as plt
from matplotlib.pyplot import Axes, Artist
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgba
from matplotlib.collections import LineCollection

from ..support.roadnet import RoadNetwork

COLORS = {
    "A00": "r",
    "A10": "g",
    "A20": "b",
    "A30": "c",
    "A40": "m",
    "A50": "#FFA500",
    "A60": "#800080",
}
NODE_COLOR = "k"


def plot_roads(
    network: RoadNetwork,
    z_order=None,
    color_roads=True,
    alpha=1,
    default_road_color="#000000",
) -> LineCollection:
    """
    Plot a RoadNetwork using matplotlib.

    Returns a Collection object that can be added to a matplotlib Axes object to
    draw roads.
    """
    segments = []
    colors = []

    for link in network:
        segments.append(link.pts_)

        if color_roads:
            colors.append(to_rgba(COLORS.get(link.type, default_road_color)))
        else:
            colors.append(to_rgba(default_road_color))

    lines = LineCollection(segments, colors=colors, zorder=z_order)
    lines.set_alpha(alpha)

    return lines


def plot_vertices(
    axes: Axes, network: RoadNetwork
) -> Tuple[Artist, List[float], List[float]]:
    """
    Plot a RoadNetwork's road network vertices using matplotlib.

    This is a convenience wrapper around Axes.scatter.

    Returns the Artist used to draw the vertices and two lists containing the
    X and Y coordinates of each vertex.
    """
    vertices = {}
    for link in network:
        vertices[link.prev] = link.pts_[0]
        vertices[link.next] = link.pts_[-1]

    node_xs = list(v[0] for v in vertices.values())
    node_ys = list(v[1] for v in vertices.values())

    return axes.scatter(node_xs, node_ys, s=10, c=NODE_COLOR), node_xs, node_ys


def _main():
    if len(sys.argv) < 2:
        sys.stderr.write(
            "USAGE: " + sys.argv[0] + " [path to road network GeoJSON file]\n"
        )
        sys.exit(1)

    # Set up figure and axes:
    fig = plt.figure()
    ax = fig.add_subplot(aspect="equal")

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        network = RoadNetwork(f)

    lines = plot_roads(network)
    ax.add_collection(lines)

    plot_roads(ax, network)

    ax.autoscale_view()
    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Road Network")

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    _main()
