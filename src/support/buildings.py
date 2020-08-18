from __future__ import annotations

import csv
import numpy as np
from typing import Dict, TextIO, Optional, Iterator


class Building:
    def __init__(
        self,
        bldg_id: int,
        center_x: float,
        center_y: float,
        area: float,
        bbox_east: float,
        bbox_west: float,
        bbox_north: float,
        bbox_south: float,
        count: Optional[int],
    ):
        self.id = bldg_id
        self.center = np.array([center_x, center_y])
        self.area = area
        self.bbox_east = bbox_east
        self.bbox_west = bbox_west
        self.bbox_north = bbox_north
        self.bbox_south = bbox_south
        self.bbox_pts = np.array(
            [
                [bbox_east, bbox_north],
                [bbox_west, bbox_north],
                [bbox_west, bbox_south],
                [bbox_east, bbox_south],
            ]
        )

        self.count = count
        if count is not None:
            self.norm_count = count / area
        else:
            self.norm_count = None

    def clone(self) -> Building:
        return Building(
            self.id,
            self.center[0],
            self.center[1],
            self.area,
            self.bbox_east,
            self.bbox_west,
            self.bbox_north,
            self.bbox_south,
            self.count,
        )


class BuildingCollection:
    def __init__(self, buildings: Dict[int, Building]):
        self.buildings = buildings

    @classmethod
    def load_csv(cls, in_file: TextIO):
        """
        Load a building data CSV file.
        
        Count data will be loaded if it is present.
        """

        buildings = {}
        reader = csv.reader(in_file)
        header = next(reader)
        has_count_col = len(header) >= 9

        for row in reader:
            bldg_id = int(row[0])
            main_args = tuple(map(float, row[1:8]))

            if has_count_col:
                count = int(row[8])
            else:
                count = None

            bldg = Building(bldg_id, *main_args, count)
            buildings[bldg.id] = bldg

        return cls(buildings)

    def __iter__(self) -> Iterator[Building]:
        return self.buildings.values().__iter__()

    def __len__(self) -> int:
        return len(self.buildings)

    def merge(self, other: BuildingCollection) -> BuildingCollection:
        """
        Merge building data from another BuildingCollection with this collection.

        Returns a new BuildingCollection with the merged data.
        """

        merged: Dict[int, Building] = dict((bldg.id, bldg.clone()) for bldg in self)
        for other_bldg in other:
            merged[other_bldg.id] = other_bldg.clone()

        return BuildingCollection(merged)
