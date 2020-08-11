import os.path as osp

from itertools import product as itprod
from math import floor
from sys import argv, exit, stderr

from matplotlib import pyplot as plt, cm
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from src.support.heatmap import comp_all, X_MIN, X_MAX, Y_MIN, Y_MAX
from src.support.emissions import EmissionsSnapshot
from src.support.roadnet import RoadNetwork

ROAD_COLOR = "#000000ff"
N_COLORS = 256


def html_to_rgba(color):
    red, green, blue, alpha = [int(color[(1 + 2*i):(3 + 2*i)], base=16) for i in range(0, 4)]
    return red, green, blue, alpha


def get_color(val, base, use_alpha=False):
    n_ranges = len(base) - 1
    for i in range(0, n_ranges):
        if i / n_ranges <= val < (i + 1) / n_ranges:
            c1, c2 = base[i], base[i + 1]
            dr, dg, db = [c2[k] - c1[k] for k in range(0, 3)]
            v = val - i / n_ranges
            if use_alpha:
                da = c2[3] - c1[3]
                alpha = floor(c1[3] + da * n_ranges * v)
            else:
                da, alpha = None, 255

            red, green, blue = \
                floor(c1[0] + dr * n_ranges * v),\
                floor(c1[1] + dg * n_ranges * v),\
                floor(c1[2] + db * n_ranges * v),
            return f'#{red:02x}{green:02x}{blue:02x}{alpha:02x}'


COLOR_BASE_1 = [html_to_rgba(color) for color in [
    '#ffffff00',
    '#eeee2b44',
    '#ee2b2b88',
    '#cc00aaff'
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


def get_rgb(x):
    red = floor(255 * x if x > 0.5 else 0)
    green = floor(255 * x if x > 0.5 else 0)
    blue = floor(255 * (1 - x) if x < 0.5 else 0)
    alpha = floor((255 * 3 - red - green - blue) / 3)
    return f'#{red:02x}{green:02x}{blue:02x}{alpha:02x}'


def plot_roads(axes, network: RoadNetwork):
    for i, link in enumerate(network.links):
        xs = list(xy[0] for xy in link.points)
        ys = list(xy[1] for xy in link.points)
        axes.add_line(Line2D(xs, ys, zorder=0, color=ROAD_COLOR))


def main():
    if len(argv) < 4:
        stderr.write(
            "USAGE: " + argv[0] + " [path to road network GEOJSON file] [path to emissions CSV snapshot file] " +
            "[path to output directory]\n"
        )
        exit(1)

    with open(argv[1], 'r', encoding='utf-8') as file:
        network = RoadNetwork(file)

    for day, hour in itprod([4, 6], range(10, 11)):
        with open(osp.join(argv[2], f'2017-07-{day:02d}_{hour:02d}_energy.csv'), 'r', encoding='utf-8') as file:
            emissions = EmissionsSnapshot.load(file)

        fig: Figure = plt.figure(figsize=(8.5, 8))
        ax = fig.add_subplot()
        # ax.set_xlabel("UTM Position (m)")
        # ax.set_ylabel("UTM Position (m)")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(X_MIN, X_MAX)
        ax.set_ylim(Y_MIN, Y_MAX)
        plot_roads(ax, network)

        hmap, link_cells, max_value = comp_all(network, emissions)
        em_norm = Normalize(0, max_value, clip=True)
        # print(f'07/{day:02d} at {hour:02d} max value = {max_value:03.3f} MMBtu')
        n_items = 3

        ax.imshow(hmap, zorder=1, cmap=HEAT_CM_2_ALPHA, extent=(X_MIN, X_MAX, Y_MIN, Y_MAX))
        # ax.set_title(f"Emissions Heat Map in Downtown Chicago,\n07/{day:02d}/2017 at {hour:02d}:00", pad=10.0,
                     # fontdict={
                       #  'fontsize': 22
                     # })

        cbar = fig.colorbar(cm.ScalarMappable(norm=em_norm, cmap=HEAT_CM_2),
                            label="Emissions Quantity (MMBtu)")
        fig.tight_layout()
        plt.savefig(osp.join(argv[3], '2017-07-{:02d}_{:02d}_heatmap.png'.format(day, hour)))
        plt.close(fig)


if __name__ == '__main__':
    main()
