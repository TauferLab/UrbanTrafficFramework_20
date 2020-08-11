import os.path as osp
from math import sqrt

from sys import argv, exit, stderr

from src.support.emissions import EmissionsSnapshot
from src.support.heatmap import comp_all, utm_to_bm, Y_MIN, Y_MAX
from src.support import VehicleMappings
from src.support.roadnet import RoadNetwork


def _get_nearest_cell(vehicle_loc, cells):
    vx, vy = utm_to_bm(vehicle_loc)
    if (vx, vy) not in cells:
        nx, ny, md = None, None, None

        for xy in cells:
            dist = sqrt((xy[0] - vx)**2 + (xy[1] - vy)**2)
            if md is None or dist <= md:
                nx, ny = xy
                md = dist
            else:
                break
        return nx, ny, md
    return vx, vy, 0


DIST_THRESHOLD = 50


def main():
    if len(argv) < 5:
        stderr.write(
            "USAGE: " + argv[0] + "[path to road network GEOJSON file] [path to CSV mappings directory] [path to CSV "
                                  "emissions directory] [output directory]\n "
        )
        exit(1)

    with open(argv[1], 'r', encoding='utf-8') as file:
        network = RoadNetwork(file)

    err = 0
    outside = 0
    total = 0
    for hour in range(3, 25):
        with open(osp.join(argv[2], f'{hour:02d}_mappings.csv'), 'r', encoding='utf-8') as file:
            vm = VehicleMappings.load(file)
        with open(osp.join(argv[3], f'2017-07-04_{hour-1:02d}_energy.csv'), 'r', encoding='utf-8') as file:
            em = EmissionsSnapshot.load(file)
        hm, link_cells, max_value = comp_all(network, em)

        for i in vm.data:
            cells = link_cells[vm.data[i].link_id]
            vx, vy, dist = _get_nearest_cell(vm.data[i].vehicle_loc, cells)
            total += 1
            if vm.data[i].vehicle_loc[1] < Y_MIN or Y_MAX < vm.data[i].vehicle_loc[1]:
                outside += 1
                err += 1
            elif dist > DIST_THRESHOLD:
                err += 1

    print(f"{err:05d} erroneous entries out of {total:05d} = {100 * err / total:2.3f}%")
    print(f"{outside:05d} entries with vehicle outside of y-bounds out of {total:05d} = {100 * outside / total:2.3f}%")


if __name__ == '__main__':
    main()
