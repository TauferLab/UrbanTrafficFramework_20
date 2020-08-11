import csv
import os.path as osp

from src.support.heatmap import X_MAX, X_MIN, BM_COLS, BM_ROWS, Y_MIN, Y_MAX
from src.support.roadnet import RoadNetwork
from sys import argv, exit, stderr

from src.support.simsio import Snapshot


DX_THRESHOLD = 30 * (X_MAX - X_MIN) / BM_COLS
DY_THRESHOLD = 30 * (Y_MAX - Y_MIN) / BM_ROWS

X_METHODS = ['USE ENDPOINT', 'USE ORIGINAL']
Y_METHODS = ['USE ENDPOINT', 'USE MIDPOINT', 'SOLVE FOR POINT']


def comp_xy(vx, a, b):
    if vx < a[0]:
        nx, x_meth = a[0], 0
    elif vx > b[0]:
        nx, x_meth = b[0], 0
    else:
        nx, x_meth = vx, 1

    if a[1] == b[1]:
        ny, y_meth = a[1], 0
    elif a[0] == b[0]:
        y_min, y_max = min(a[1], b[1]), max(a[1], b[1])
        ny, y_meth = (y_max - y_min) / 2, 1
    else:
        m = (b[1] - a[1]) / (b[0] - a[0])
        y_int = a[1] - m * a[0]
        ny, y_meth = m * nx + y_int, 2

    return nx, ny, x_meth, y_meth


def main():
    if len(argv) < 4:
        stderr.write(
            f"USAGE: {argv[0]} [path to road network GEOJSON file] [path to simulation snapshot CSV directory] "
            f"[output directory for new dataset] [generate reports = true | false]"
        )
        exit(1)

    gen_reports = argv[4] == 'true'
    with open(argv[1], 'r', encoding='utf-8') as file:
        network = RoadNetwork(file)

    err_x, err_y, outside_x, outside_y, err_total, total = 0, 0, 0, 0, 0, 0
    methods = {}
    for hour in range(0, 25):
        if gen_reports:
            file = open(osp.join(argv[3], f'report_Snapshot_{hour*10**6:d}.csv'), 'w', encoding='utf-8', newline='')
            cr_writer = csv.writer(file)
            cr_writer.writerow(['VEHICLE', 'TIME', 'LINK', 'A_X', 'A_Y', 'B_X', 'B_Y', 'OLD_X_COORD', 'OLD_Y_COORD',
                                'X_METHOD', 'Y_METHOD', 'NEW_X_COORD', 'NEW_Y_COORD', 'DIFF_X', 'DIFF_Y'])
        else:
            cr_writer = None

        with open(osp.join(argv[2], f'Snapshot_{hour*10**6:d}.csv'), 'r', encoding='utf-8') as file:
            ss = Snapshot.load(file)
        total += len(ss.frames)

        for frame in ss.frames:
            start = network.links[frame.link].points[0]
            end = network.links[frame.link].points[1]
            if start[0] < end[0]:
                a = start
                b = end
            else:
                a = end
                b = start

            err_coords = 0
            if frame.x < X_MIN or X_MAX < frame.x:
                outside_x += 1
                err_x += 1
                err_coords += 1
            elif frame.x < a[0] - DX_THRESHOLD or b[0] + DX_THRESHOLD < frame.x:
                err_x += 1
                err_coords += 1

            if frame.y < Y_MIN or Y_MAX < frame.y:
                outside_y += 1
                err_y += 1
                err_coords += 1
            elif frame.y < min(a[1], b[1]) - DY_THRESHOLD or max(a[1], b[1]) + DY_THRESHOLD < frame.y:
                err_y += 1
                err_coords += 1

            if err_coords > 0:
                err_total += 1

            old_x, old_y = frame.x, frame.y
            frame.x, frame.y, x_meth, y_meth = comp_xy(frame.x, a, b)
            if (x_meth, y_meth) not in methods:
                methods[(x_meth, y_meth)] = 1
            else:
                methods[(x_meth, y_meth)] += 1

            if gen_reports:
                cr_writer.writerow([frame.vid, frame.timestamp(), frame.link, a[0], a[1], b[0], b[1],
                                    old_x, old_y, X_METHODS[x_meth], Y_METHODS[y_meth],
                                    frame.x, frame.y, frame.x - old_x, frame.y - old_y])
        print(f"{100 * (hour + 1)/25:3.2f}% of data processed")

        with open(osp.join(argv[3], f'Snapshot_{hour*10**6:d}.csv'), 'w', encoding='utf-8', newline='') as file:
            ss.write(file)

    print("Error rates prior to reinterpretation:")
    print(f"{err_x:05d} erroneous x-coordinates out of {total:05d} total entries = {err_x * 100 / total:3.3f}%")
    print(f"{outside_x:05d} of these were outside the map, rate of occurrence = {outside_x * 100 / total:3.3f}%")
    print(f"{err_y:05d} erroneous y-coordinates out of {total:05d} total entries = {err_y * 100 / total:3.3f}%")
    print(f"{outside_y:05d} of these were outside the map, rate of occurrence = {outside_y * 100 / total:3.3f}%")
    print(f"{err_total:05d} erroneous entries in total, rate of occurrence = {err_total *100 / total:3.3f}%")
    for xym in methods:
        print(f"{methods[xym]:05d} entries were corrected as follows: method for x-coord was \"{X_METHODS[xym[0]]}\", "
              f"method for y-coord was \"{Y_METHODS[xym[1]]}\"")


if __name__ == '__main__':
    main()