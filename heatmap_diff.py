from csv import writer as CSVWriter
from itertools import product as itprod
from os import path as osp

from support import heatmap
from support.emissions import EmissionsSnapshot
from support.roadnet import RoadNetwork
from sys import argv, exit, stderr

def main():
    if len(argv) < 3:
        stderr.write(
            f"USAGE: {argv[0]} [path to road network] [path to emissions directory]\n"
        )
        exit(1)

    with open(argv[1], 'r', encoding='utf-8') as file:
        network = RoadNetwork(file)

    result = [{}] * 24
    for hour in range(0, 24):
        maps = {}
        for day in range(4, 11):
            with open(osp.join(argv[2], f'2017-07-{day:02d}_{hour:02d}_energy.csv'), 'r', encoding='utf-8') as file:
                emissions = EmissionsSnapshot.load(file)

            maps[day] = heatmap.comp_values(network, emissions)[0]
            for prev in range(4, day):
                result[hour][(prev, day)] = heatmap.comp_diff(maps[prev], maps[day])
                print(f"Computed difference for hour {hour:02d}, days {prev:02d} and {day:02d}")

    with open('data/heatmap_diffs.csv', 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = CSVWriter(csv_file)
        csv_writer.writerow(["Day 1", "Day 2", "Hour", "Difference"])

        for hour, diffs in enumerate(result):
            for day1, day2 in diffs.keys():
                csv_writer.writerow([day1, day2, hour, diffs[(day1, day2)]])


if __name__ == '__main__':
    main()
