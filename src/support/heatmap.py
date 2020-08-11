from typing import Dict, List, Tuple

import numpy as np

from itertools import product as itprod
from math import floor
from math import sqrt
from src.support.emissions import EmissionsSnapshot
from src.support.roadnet import RoadNetwork

BM_COLS = 400
BM_ROWS = 550
X_MIN, X_MAX = 446319.62563207, 448913.35313896
Y_MIN, Y_MAX = 4634587.13680183, 4638130.74608598

# Coordinate-transformation standard matrix
CT_STDMAT = np.array([
    [(BM_COLS - 1) / (X_MAX - X_MIN), 0],
    [0, (BM_ROWS - 1) / (Y_MIN - Y_MAX)]
])

# Coordinate-transformation offset
CT_OFFSET = np.array([
    (1 - BM_COLS) * X_MIN / (X_MAX - X_MIN),
    (1 - BM_ROWS) * Y_MAX / (Y_MIN - Y_MAX)
])


# Convert UTM coords to bitmap coords
def utm_to_bm(utm_pair):
    return CT_STDMAT.dot(utm_pair) + CT_OFFSET


CUTOFF_DISTANCE = 8
SCALE_FACTOR = 0.001


def comp_affect(em: float, radius: float) -> float:
    return em if radius == 0 else em / radius


def aff_area_bbox(start: Tuple[float, float], end: Tuple[float, float]) -> Tuple[int, int, int, int]:
    x_min = floor(min(start[0], end[0]) - CUTOFF_DISTANCE)
    x_max = floor(max(start[0], end[0]) + CUTOFF_DISTANCE)
    y_min = floor(min(start[1], end[1]) - CUTOFF_DISTANCE)
    y_max = floor(max(start[1], end[1]) + CUTOFF_DISTANCE)
    return x_min, y_min, x_max, y_max


def comp_diff(m1: [[float]], m2: [[float]]) -> float:
    result = 0
    diff_mat = m2 - m1
    for i in range(0, BM_ROWS):
        result += diff_mat[i].dot(diff_mat[i])
    return sqrt(result)


ij_pairs = []
for _i, _j in itprod(range(-CUTOFF_DISTANCE, CUTOFF_DISTANCE + 1), range(-CUTOFF_DISTANCE, CUTOFF_DISTANCE + 1)):
    r = sqrt(_i*_i + _j*_j)
    if r <= CUTOFF_DISTANCE:
        ij_pairs.append((_i, _j, r))


def comp_all(network: RoadNetwork, emissions: EmissionsSnapshot) ->\
        Tuple[List[List[float]], Dict[int, List[Tuple[int, int]]], float]:

    result = np.zeros((BM_ROWS, BM_COLS), dtype=float)
    link_cells: Dict[int, List[Tuple[int, int]]] = {}

    max_value = 0
    for link in network.links:
        if link.id not in emissions.data:
            continue

        # Get endpoints for link in bitmap coords
        start = utm_to_bm(np.array([link.points[0][0], link.points[0][1]]))
        end = utm_to_bm(np.array([link.points[1][0], link.points[1][1]]))

        if start[0] < end[0]:
            a = start
            b = end
        else:
            a = end
            b = start

        x_min, x_max = floor(a[0]), floor(b[0])
        y_min, y_max = (floor(a[1]), floor(b[1])) if a[1] < b[1] else (floor(b[1]), floor(a[1]))
        if x_min == x_max:
            src_cells = [(x_min, y) for y in range(y_min, y_max + 1)]
        elif y_min == y_max:
            src_cells = [(x, y_min) for x in range(x_min, x_max + 1)]
        else:
            m = (b[1] - a[1]) / (b[0] - a[0])
            y_int = a[1] - m * a[0]
            src_cells = [(x, floor(m * x + y_int)) for x in range(x_min, x_max + 1)]
        link_cells[link.id] = []

        for src in src_cells:
            for i, j, radius in ij_pairs:
                x, y = src[0] + j, src[1] + i
                if 0 <= x < BM_COLS and 0 <= y < BM_ROWS:
                    link_cells[link.id].append((x, y))
                    em = emissions.data[link.id]
                    result[y][x] += comp_affect(em.quantity, radius)
                    if result[y][x] > max_value:
                        max_value = result[y][x]

    return result, link_cells, max_value
