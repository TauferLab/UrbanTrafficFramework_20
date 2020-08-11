import json
import numpy as np
from typing import Tuple, List, Dict

from .utm import convert_to_utm


CENT_LON = -87


class Link:
    def __init__(self, prevl, nextl, link_id, direct, points, link_type):
        self.prev: int = prevl
        self.next: int = nextl
        self.direct: int = direct
        self.points: List[Tuple[float, float]] = points
        self.id: int = link_id
        self.type: str = link_type

        # calculate length:
        prev = self.points[0]
        self.length: float = 0

        for cur in self.points[1:]:
            self.length += np.hypot(cur[0] - prev[0], cur[1] - prev[1])
            prev = cur

    def offset_to_point(self, offset: float, direct: int) -> Tuple[float, float]:
        if direct != self.direct:
            points = reversed(self.points)
        else:
            points = self.points.__iter__()

        prev_len = 0
        prev = next(points)
        for cur in points:
            l = np.hypot(cur[0] - prev[0], cur[1] - prev[1])
            cur_len = prev_len + l

            if cur_len < offset:
                prev_len = cur_len
                prev = cur
                continue

            s = (offset - prev_len) / l
            x = (s * cur[0]) + ((1 - s) * prev[0])
            y = (s * cur[1]) + ((1 - s) * prev[1])

            return (x, y)

        raise ValueError(
            "Offset {} out of bounds for link with length {}".format(offset, prev_len)
        )

    def total_length(self) -> float:
        return self.length


class RoadNetwork:
    def __init__(self, fp):
        self.links: List[Link] = []

        obj = json.load(fp)
        features = obj["features"]
        for feature in features:
            prop, coords = feature["properties"], feature["geometry"]["coordinates"]
            linkid, prevl, nextl, direct = (
                int(prop["LINKID"]),
                int(prop["FROM"]),
                int(prop["TO"]),
                int(prop["DIRECT"]),
            )

            points = [convert_to_utm(c[1], c[0], CENT_LON) for c in coords]
            self.links.insert(
                linkid, Link(prevl, nextl, linkid, direct, points, prop["FCC"])
            )

        self.links = sorted(self.links, key=lambda l: l.id)
