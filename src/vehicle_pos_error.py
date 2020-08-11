# Computes the distance between the computed position and the listed position
# for sampled records from the traffic simulation dataset.
#
# Run as:
# ~$ python3 vehicle_pos_error.py [path to challenge 4 datasets]
# Make sure to run this from the repository root!

import os.path as osp
import sys
import csv
import numpy as np
import multiprocessing as mp

from src.support import roadnet

SAMPLED_RECORDS = 1242228

def read_records():
    i = 0

    with open("data/sim_sample.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            i += 1
            if i % 50000 == 0:
                sys.stderr.write("Progress: {:.1%}\n".format(i / SAMPLED_RECORDS))
                sys.stderr.flush()
        
            yield row
        


NETWORK = None
def _init(data_dir):
    global NETWORK

    ROAD_NETWORK = osp.join(data_dir, "Road Network", "RoadNetwork.geojson")
    with open(ROAD_NETWORK, "r", encoding="utf-8") as f:
        NETWORK = roadnet.RoadNetwork(f)


def _map_func(row):
    global NETWORK

    vehicle = int(row[0])
    time = row[1]
    link = int(row[2])
    direct = int(row[3])
    offset = float(row[5])
    data_x = float(row[11])
    data_y = float(row[12])

    try:
        road = NETWORK.links[link]
        calc_x, calc_y = road.offset_to_point(offset, direct)
    except ValueError:
        return None
    
    return (vehicle, time, np.around(np.hypot(calc_x - data_x, calc_y - data_y), 3),)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("USAGE: " + sys.argv[0] + " [path to datasets]\n")
        sys.stderr.flush()
        sys.exit(1)

    with mp.Pool(None, _init, [sys.argv[1]]) as pool:
        i = 0

        with open("data/simulation_position_errors.csv", "w", encoding="utf-8") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["vehicle", "time", "position_err_m"])
            writer.writerows(filter(lambda r: r is not None, pool.imap_unordered(_map_func, read_records(), 10000)))
    