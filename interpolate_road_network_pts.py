import numpy as np
import csv
import sys

from support import roadnet

SPACING = 2.5


def main():
    # Load the network:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        network = roadnet.RoadNetwork(f)

    with open(sys.argv[2], "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "link_id", "offset"])

        # For every link, interpolate along the link's segments to generate a 
        # series of points that we can snap to:
        for i, link in enumerate(network.links):
            prev = link.points[0]
            offset = 0

            for point in link.points[1:]:
                segment_len = np.hypot(point[0] - prev[0], point[1] - prev[1])

                for d in np.arange(0, segment_len, step=SPACING):
                    s = d / segment_len
                    x = np.around((s * point[0]) + ((1 - s) * prev[0]), 2)
                    y = np.around((s * point[1]) + ((1 - s) * prev[1]), 2)
                    
                    writer.writerow([x, y, link.id, offset + d])
                
                offset += segment_len
                prev = point

            last = link.points[-1]
            writer.writerow([np.around(last[0], 2), np.around(last[1], 2), link.id, offset])

            if (i+1) % 100 == 0:
                sys.stderr.write("Progress: {:.1%}\n".format((i+1) / len(network.links)))
                sys.stderr.flush()

if __name__ == "__main__":
    main()
