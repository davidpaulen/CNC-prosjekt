import numpy as np
from .config import *
from .utils import *


def transform_points_to_mm(points, h):
    return [
        (
            OFFSET_X + x * MM_PER_PIXEL * SCALE_FACTOR,
            OFFSET_Y + (h - y) * MM_PER_PIXEL * SCALE_FACTOR
        )
        for x, y in points
    ]


def distance(a, b):
    return float(np.hypot(b[0]-a[0], b[1]-a[1]))


def normalize_paths_to_origin(paths, ox, oy):
    min_x = min(x for p in paths for x,y in p)
    min_y = min(y for p in paths for x,y in p)

    return [
        [(x-min_x+ox, y-min_y+oy) for x,y in path]
        for path in paths
    ]


def check_bounds(paths):
    for path in paths:
        for x,y in path:
            if x<0 or x>BED_WIDTH_MM:
                fail("X utanfor")
            if y<0 or y>BED_HEIGHT_MM:
                fail("Y utanfor")