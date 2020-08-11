import sys
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from src.support.roadnet import RoadNetwork

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


def plot_roads(axes, network: RoadNetwork, z_order=None, color_roads=True, plot_nodes=True,
               alpha=1, default_road_color='#000000'):
    vertices = {}

    for i, link in enumerate(network.links):
        xs = list(xy[0] for xy in link.points)
        ys = list(xy[1] for xy in link.points)
        vertices[link.prev] = link.points[0]
        vertices[link.next] = link.points[-1]

        if color_roads:
            color = COLORS[link.type] if link.type in COLORS else default_road_color
        else:
            color = 'k'

        axes.add_line(Line2D(xs, ys, alpha=alpha, color=color, zorder=z_order))

        if i % 500 == 0:
            print(
                "Collecting points and road segments: {:.1%}".format((i + 1) / len(network.links))
            )

    node_xs = list(v[0] for v in vertices.values())
    node_ys = list(v[1] for v in vertices.values())

    if plot_nodes:
        # Render road network nodes:
        axes.scatter(node_xs, node_ys, s=10, c=NODE_COLOR)

    return node_xs, node_ys


def main():
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

    plot_roads(ax, network)
    ax.autoscale_view()

    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Road Network")

    plt.show()


if __name__ == "__main__":
    main()
