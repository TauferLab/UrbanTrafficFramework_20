from __future__ import annotations

import csv
from typing import Dict, TextIO, Iterator


class LinkEmissions(object):
    def __init__(self, link_id: int, rate: float, quantity: float):
        self.link = link_id
        self.rate = rate  # kJ / vehicle / operating hour
        self.quantity = quantity  # MMBtu

    def emission_rate(self) -> float:
        """Return the heat emission rate on this link, in units of W/vehicle."""
        # (kJ / vehicle / op. hour) * (1000 J / 1 kJ) * (1 hr / 3600 s)
        #  = (J / vehicle / op. second) = (W / vehicle)
        return self.rate * (1000 / 3600)

    def emission_quantity(self) -> float:
        """Get the quantity of heat emitted on this link, in units of joules."""
        # 1 MMBtu = 1,000,000 BTU
        # 1 BTU = 1.05506 kJ
        return self.quantity * 1000000 * 1055.06

    def temperature_elevation(self, link_area_m: float) -> float:
        """Get the expected ambient temperature elevation for this link due to
        vehicle exhaust.

        Parameters:
            link_area_m (float): Square area of link in meters^2.

        Returns:
            Ambient temperature elevation for this link, in degrees Celcius.
        """
        # First divide emission quantity by 3600 to get W, then divide by link
        # area to get W/m^2.
        #
        # According to the readme, the expected air temp increase due to traffic
        # exhaust is around 0.8 C per 100 W/m^2.
        return (self.emission_quantity() / 3600 / link_area_m) * (0.8 / 100)


class EmissionsSnapshot(object):
    def __init__(self):
        self.data: Dict[int, LinkEmissions] = {}

    @classmethod
    def load(cls, fp: TextIO) -> EmissionsSnapshot:
        ret = cls()
        reader = csv.reader(fp)
        next(reader)

        for row in reader:
            link_data = LinkEmissions(int(row[1]), float(row[3]), float(row[4]))
            ret.data[link_data.link] = link_data

        return ret

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator[LinkEmissions]:
        return self.data.values().__iter__()
