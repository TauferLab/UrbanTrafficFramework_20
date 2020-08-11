from __future__ import annotations

import csv
import os.path as osp

from itertools import product as itprod
from math import floor

from support.emissions import EmissionsSnapshot
from support.heatmap import comp_all, utm_to_bm, BM_ROWS, BM_COLS
from support.roadnet import RoadNetwork
from sys import argv, exit, stderr


class Building:
    def __init__(self, bid: int, bx: float, by: float, area: float,
                 east: float, west: float, north: float, south: float, count: int):
        self.building_id = bid
        self.location = (bx, by)
        self.area = area
        self.east = east
        self.west = west
        self.north = north
        self.south = south
        self.count = count

    @classmethod
    def parse_row(cls, row) -> Building:
        return cls(
            int(row[0]),
            float(row[1]),
            float(row[2]),
            float(row[3]),
            float(row[4]),
            float(row[5]),
            float(row[6]),
            float(row[7]),
            int(row[8])
        )


def main():
    if len(argv) < 5:
        stderr.write(
            f"USAGE: {argv[0]} [path to road network GEOJSON file] [path to CSV emissions directory] "
            f"[path to CSV building counts directory] [path to output directory]"
        )
        exit(1)

    with open(argv[1], 'r', encoding='utf-8') as file:
        network = RoadNetwork(file)

    for hour in range(3, 25):
        with open(osp.join(argv[2], f'2017-07-04_{hour-1:02d}_energy.csv'), 'r', encoding='utf-8') as file:
            emissions = EmissionsSnapshot.load(file)

        hm = comp_all(network, emissions)

        with open(osp.join(argv[3], f'{hour:02d}_counts.csv'), 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)
            buildings = []
            for row in reader:
                bldg = Building.parse_row(row)
                buildings.append(bldg)

        with open(osp.join(argv[4], f'building_em_density_{hour:02d}.csv'), 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['BUILDING', 'BUILDING_X', 'BUILDING_Y', 'BUILDING_AREA', 'EMISSIONS_TOTAL',
                             'MAPPED_VEHICLE_COUNT', 'EMISSIONS_CONCENTRATION'])
            for bldg in buildings:
                sw_corner = utm_to_bm((bldg.west, bldg.south))
                ne_corner = utm_to_bm((bldg.east, bldg.north))
                x_min, x_max, y_min, y_max = (
                    floor(sw_corner[0]),
                    floor(ne_corner[0]),
                    floor(ne_corner[1]),
                    floor(sw_corner[1])
                )
                em_total = 0
                for i, j in itprod(range(y_min, y_max + 1), range(x_min, x_max + 1)):
                    if i < 0 or BM_ROWS <= i or j < 0 or BM_COLS <= j:
                        continue
                    em_total += hm[0][i][j]
                writer.writerow([bldg.building_id, bldg.location[0], bldg.location[1], bldg.area, em_total,
                                     bldg.count, em_total / bldg.area])


if __name__ == '__main__':
    main()
