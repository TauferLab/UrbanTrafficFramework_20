from math import floor
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import os.path as osp
import src.support.linkvolio as lvio
import src.support.roadnet as rnio
import sys
from sys import argv
from sys import stderr


day_str_dict = {
    "Monday": "MONDAY",
    "Tuesday": "TUESDAY",
    "Wednesday": "WEDNESDAY",
    "Thursday": "THURSDAY",
    "Friday": "FRIDAY"
}

MAX_VOLUME = 1200


def comp_color(volume):
    if volume == 0:
        return '#b3b3b3'

    red = floor(255 * volume / MAX_VOLUME)
    if red > 255:
        red = 255
    green = floor(255 * volume * volume / (8 * MAX_VOLUME * MAX_VOLUME))
    if green > 255:
        green = 255
    return '#{:02x}{:02x}00'.format(red, green)


def plot_volumes(axes, volumes, network, day, hour):
    vertices = {}

    for i, link in enumerate(network.links):
        xs = list(xy[0] for xy in link.points)
        ys = list(xy[1] for xy in link.points)
        vertices[link.prev] = link.points[0]
        vertices[link.next] = link.points[-1]

        if volumes[i] is None:
            color = '#9975bd'
        else:
            color = comp_color(volumes[i].link_vol)
        axes.add_line(Line2D(xs, ys, color=color))

        if i % 500 == 0:
            print(
                "Collecting points and road segments: {:.1%}".format((i + 1) / len(network.links))
            )

    node_xs = list(v[0] for v in vertices.values())
    node_ys = list(v[1] for v in vertices.values())

    return node_xs, node_ys


def main():
    if len(argv) < 5:
        stderr.write(
            "USAGE: " + argv[0] + "[path-to-volume-files] [path-to-road-network-file] [day] [hour]\n"
        )
        sys.exit(1)

    # Get the human-readable name of the day and the integer value for the hour we want to load
    day, hour = argv[3], int(argv[4])

    # Get the volumes for this time
    with open(osp.join(argv[1], day + '_' + str(hour) + '.csv'), 'r', encoding='utf-8') as vol_file:
        volumes = lvio.link_volumes(vol_file)

    # Load the road network to plot underneath
    with open(argv[2], 'r', encoding='utf-8') as rn_file:
        roads = rnio.RoadNetwork(rn_file)

    fig = plt.figure()
    ax = fig.add_subplot(aspect='equal')

    plot_volumes(ax, volumes, roads, day, hour)
    ax.autoscale_view()

    ax.set_xlabel("Position (m)")
    ax.set_ylabel("Position (m)")
    ax.set_title("Road Link Volumes on " + day + " at hour " + str(hour))

    plt.show()


if __name__ == "__main__":
    main()
