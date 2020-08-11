from __future__ import annotations
import csv
import os.path as osp
from typing import TextIO, Dict


class MappingEntry:
    def __init__(self, bid: int, vid: int, lid: int, vx: float, vy: float,
                 bx: float, by: float, dist: float, vcount: int):
        self.vehicle_id = vid
        self.link_id = lid
        self.vehicle_loc = (vx, vy)
        self.building_id = bid
        self.building_loc = (bx, by)
        self.distance = dist
        self.vehicles = vcount

    @classmethod
    def parse_csv(cls, row) -> MappingEntry:
        return cls(int(row[4]), int(row[0]), int(row[1]), float(row[2]), float(row[3]),
                   float(row[5]), float(row[6]), float(row[7]), int(row[8]))


class VehicleMappings:
    def __init__(self):
        self.data: Dict[int, MappingEntry] = {}

    def add_entry(self, entry: MappingEntry) -> MappingEntry:
        self.data[entry.building_id] = entry
        return entry

    @classmethod
    def load(cls, fp: TextIO) -> VehicleMappings:
        result = cls()
        reader = csv.reader(fp)
        next(reader)
        for row in reader:
            result.add_entry(MappingEntry.parse_csv(row))
        return result
