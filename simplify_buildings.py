import csv
import sys
import ijson
import numpy as np
from support.utm import convert_to_utm

CENT_LON = -87


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "USAGE: "
            + sys.argv[0]
            + " [path to building footprints GeoJSON data] [output file]\n"
        )
        sys.exit(1)

    with open(sys.argv[1], "rb") as infile:
        with open(sys.argv[2], "w", encoding="utf-8") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(
                [
                    "id",           # Building ID
                    "center_x",     # Centroid X
                    "center_y",     # Centroid Y
                    "area",         # Footprint Area (m^2)
                    "bbox_east",    # X-coordinate of bounding-box east side  (+X)
                    "bbox_west",    # X-coordinate of bounding-box west side  (-X)
                    "bbox_north",   # Y-coordinate of bounding-box north side (+Y)
                    "bbox_south",   # Y-coordinate of bounding-box south side (-Y)
                ]
            )

            min_coords = np.array([-87.651190, 41.848287])
            max_coords = np.array([-87.609778, 41.900419])

            i = 0
            n = 0
            for coords in ijson.items(
                infile, "features.item.geometry.coordinates", use_float=True,
                buf_size=1048576
            ):
                n += 1
                if n % 50000 == 0:
                    print("Processed {} buildings...".format(n))

                coords = np.array(coords[0])

                #if min_coords is None:
                #    min_coords = np.amin(coords, axis=0)
                #    max_coords = np.amax(coords, axis=0)
                #else:
                #    min_coords = np.fmin(
                #        np.amin(coords, axis=0),
                #        min_coords
                #    )

                #    max_coords = np.fmax(
                #        np.amax(coords, axis=0),
                #        max_coords
                #    )

                if np.count_nonzero((coords < min_coords) | (coords > max_coords)) > 0:
                    continue

                x, y = convert_to_utm(coords[:, 1], coords[:, 0], CENT_LON)
                area = 0.5 * np.abs(np.sum(x * np.roll(y, 1) - y * np.roll(x, 1)))

                writer.writerow(
                    (
                        i,
                        np.around(np.mean(x), 2),
                        np.around(np.mean(y), 2),
                        np.around(area, 2),
                        np.around(np.max(x), 2),
                        np.around(np.min(x), 2),
                        np.around(np.max(y), 2),
                        np.around(np.min(y), 2),
                    )
                )

                i += 1


if __name__ == "__main__":
    main()
