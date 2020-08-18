import json
import numpy as np
from typing import Tuple, List, Dict, IO, Iterator

from .utm import convert_to_utm, S_MAJ


CENT_LON = -87


def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees)

    All args must be of equal length.    
    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2

    c = 2 * np.arcsin(np.sqrt(a))
    m = S_MAJ * c
    return m


class Link:
    def __init__(self, prevl, nextl, link_id, direct, coords, link_type):
        self.prev: int = prevl
        self.next: int = nextl
        self.direct: int = direct
        self.coords: np.ndarray = np.array(coords)
        self.pts_ = np.column_stack(
            convert_to_utm(self.coords[:, 1], self.coords[:, 0], CENT_LON)
        )
        self.points: List[np.ndarray] = [
            a.squeeze() for a in np.vsplit(self.pts_, self.pts_.shape[0])
        ]
        self.id: int = link_id
        self.type: str = link_type

        # lon/lat 1: start from 0, but don't include the end
        lon1 = self.coords[:-1, 0]
        lat1 = self.coords[:-1, 1]

        # lon/lat 2: include the end, but start from 1
        lon2 = self.coords[1:, 0]
        lat2 = self.coords[1:, 1]

        # all 4 of the above array views have length n-1 (where n = # of coords)
        # however, lon2/lat2 are offset by 1 compared to lon1/lat1
        # (i.e. lon1[0] = coords[0, 0], lon2[0] = coords[1, 0], and so on)
        segment_lengths = haversine_np(lon1, lat1, lon2, lat2)

        self.seg_lengths: np.ndarray = segment_lengths
        self.cum_lengths: np.ndarray = np.cumsum(segment_lengths)
        self.rev_lengths: np.ndarray = np.cumsum(np.flip(segment_lengths))
        self.length: float = float(self.cum_lengths[-1])

    def offset_to_point(self, offset: float, direct: int) -> Tuple[float, float]:
        if direct == self.direct:
            cum_lengths = self.cum_lengths
            seg_lengths = self.seg_lengths
            coords = self.coords
        else:
            cum_lengths = self.rev_lengths
            seg_lengths = np.flip(self.seg_lengths)
            coords = np.flip(self.coords, axis=0)

        # Get the index of the first element in cum_lengths that is >= offset.
        # np.nonzero returns a tuple of ndarrays (one ndarray for each dimension).
        #
        # Additionally, cum_lengths is 1-D, so np.nonzero only ever returns a
        # length-1 tuple.
        try:
            seg_idx = np.nonzero(cum_lengths >= offset)[0][0]
        except IndexError:
            raise ValueError(
                "Offset {} out of bounds for link with length {}".format(
                    offset, self.length
                )
            )

        # self.cum_lengths and self.rev_lengths always have one less element
        # than self.coords, so this indexing should always work:
        p1 = coords[seg_idx]
        p2 = coords[seg_idx + 1]
        t = (cum_lengths[seg_idx] - offset) / seg_lengths[seg_idx]
        interpolated = (t * p1) + ((1 - t) * p2)

        return convert_to_utm(interpolated[1], interpolated[0], CENT_LON)

    def total_length(self) -> float:
        return self.length


class RoadNetwork:
    def __init__(self, fp: IO):
        self.links: Dict[int, Link] = {}
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

            self.links[linkid] = Link(prevl, nextl, linkid, direct, coords, prop["FCC"])

    def __iter__(self) -> Iterator[Link]:
        return self.links.values().__iter__()

    def __len__(self) -> int:
        return len(self.links)

    def enumerate(self) -> Iterator[Tuple[int, Link]]:
        return self.links.items().__iter__()

    def bbox(self) -> Tuple[np.ndarray, np.ndarray]:
        mins = []
        maxes = []

        for road in self:
            mins.append(np.amin(road.pts_, axis=0))
            maxes.append(np.amax(road.pts_, axis=0))

        bbox_ne = np.amax(maxes, axis=0)
        bbox_sw = np.amin(mins, axis=0)

        return bbox_ne, bbox_sw

