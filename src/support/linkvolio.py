import csv


LINK_DESC = []
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]


class LinkVolume:
    def __init__(
        self,
        link_id: int,
        cty_id: int,
        zone_id: int,
        road_t: int,
        length: float,
        volume: float,
        avg_speed: float,
        desc: int,
        avg_grade: float,
    ):
        self.link_id = link_id
        self.county_id = cty_id
        self.zone_id = zone_id
        self.road_type = road_t
        self.link_len = length
        self.link_vol = volume
        self.avg_speed = avg_speed
        self.desc = desc
        self.avg_grade = avg_grade


def link_volumes(fp):
    result = {}
    reader = csv.reader(fp, delimiter=",")
    next(reader)

    for row in reader:
        lid = int(row[0])
        cid = int(row[1])
        zid = int(row[2])
        rt = int(row[3])
        link_len = float(row[4])
        link_vol = int(row[5])
        avg_sp = float(row[6])
        avg_gr = float(row[8])

        try:
            # Attempt to find the link description in LINK_DESC
            desc = LINK_DESC.index(row[7])
        except ValueError:
            # Not found-- append the description to LINK_DESC
            desc = len(LINK_DESC)
            LINK_DESC.append(row[7])

        result[lid] = LinkVolume(
            lid, cid, zid, rt, link_len, link_vol, avg_sp, desc, avg_gr
        )

    return result


class VolumeSnapshot:
    def __init__(self):
        self.volumes = {key: [[]] * 24 for key in DAYS}
        self.links = []

    def insert_volume(self, day, hour, lv):
        lv_array = self.volumes[day][hour]

        if len(lv_array) <= lv.link_id:
            lv_array.extend([None] * (lv.link_id - len(lv_array) + 1))
        lv_array[lv.link_id] = lv

        if len(self.links) <= lv.link_id:
            self.links.extend(
                [{key: [[]] * 24 for key in DAYS}] * (lv.link_id - len(lv_array) + 1)
            )
        self.links[lv.link_id][day][hour] = lv
