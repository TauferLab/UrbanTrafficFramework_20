import sys
import csv
import numpy as np
from scipy.spatial import cKDTree   # pylint: disable=no-name-in-module

from support.simsio import Snapshot

MAX_SNAP_DISTANCE = 20.0

def load_network_points():
    points = []
    associated_links = []
    offsets = []

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(f)

        for row in reader:
            points.append((float(row[0]), float(row[1])))
            associated_links.append(int(row[2]))
            offsets.append(float(row[3]))

    return np.array(points), associated_links, offsets


def main():
    network_pts, links, offsets = load_network_points()
    kd_tree = cKDTree(network_pts)

    with open(sys.argv[2], "r", encoding="utf-8") as f:
        snapshot = Snapshot.load(f)
    
    with open(sys.argv[3], "w", encoding="utf-8") as outf:
        writer = csv.writer(outf)
        writer.writerow(["vehicle", "time", "link", "dir", "lane", "offset", "speed", "accel", "veh_type", "driver", "passengers", "x_coord", "y_coord", "true_x", "true_y", "dist"])

        for trace in snapshot.iter_traces():
            trace_points = [(frame.x, frame.y) for frame in trace]

            # For each vehicle trace point, get the nearest point in the interpolated
            # road network:
            dists, indices = kd_tree.query(trace_points, distance_upper_bound=MAX_SNAP_DISTANCE)

            for frame, dist, point_idx in zip(trace, dists, indices):
                # dist = distance to nearest neighbor in network_pts list
                # point_idx = index of nearest neighbor in network_pts

                if point_idx == kd_tree.n:
                    # no nearest neighbor found within MAX_SNAP_DISTANCE
                    continue
                
                # network_pts, links, and offsets all share the same ordering,
                # so we can use point_idx to get anassociated link and offset
                # for each frame:
                x, y = network_pts[point_idx] 
                link = links[point_idx]
                offset = offsets[point_idx]
                writer.writerow([frame.vid, frame.timestamp(), link, 0, frame.lane, offset, 0, 0, 0, frame.driver, 0, x, y, frame.x, frame.y, dist])

if __name__ == "__main__":
    main()
