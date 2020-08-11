# Takes a random sample of vehicle positions (from the entire merged vehicle
# simulation dataset) for further analysis.
#
# Run as:
# ~$ python3 sample_vehicle_data.py [path to challenge 4 datasets]
# Make sure to run this from the repository root!

import os.path as osp
import sys
import csv
import numpy as np
from numpy.random import SeedSequence, default_rng
import multiprocessing as mp

SAMPLE_PROPORTION = 0.05
SEED = 1592417421
N_FILES = 25


def _generate_args(data_dir):
    vehicle_data = osp.join(data_dir, "Vehicle Data", "Simulation Snapshot")
    ss = SeedSequence(SEED)
    seeds = ss.spawn(N_FILES)

    for chunk in range(N_FILES):
        fname = osp.join(vehicle_data, "Snapshot_" + str(chunk * 1000000) + ".csv")

        sys.stderr.write("Processing chunk {}...\n".format(chunk))
        sys.stderr.flush()

        yield (seeds[chunk], fname)


def _map_func(args):
    seed, fname = args
    rng = default_rng(seed)
    records = []

    with open(fname, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            if rng.random() >= SAMPLE_PROPORTION:
                continue
            records.append(row)

    return records


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("USAGE: " + sys.argv[0] + " [path to datasets]\n")
        sys.stderr.flush()
        sys.exit(1)

    with mp.Pool(None) as pool:
        with open("data/sim_sample.csv", "w", encoding="utf-8") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["VEHICLE", "TIME", "LINK", "DIR", "LANE", "OFFSET", "SPEED", "ACCEL", "VEH_TYPE", "DRIVER", "PASSENGERS", "X_COORD", "Y_COORD"])

            for rows in pool.imap_unordered(_map_func, _generate_args(sys.argv[1])):
                writer.writerows(rows)
