import cv2
from .config import *
from .utils import *


def find_valid_contours(binary):
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    valid = [c for c in contours if cv2.contourArea(c) > MIN_CONTOUR_AREA]

    if not valid:
        fail("Ingen konturar")

    return valid


def smooth_contour(c):
    return c


def contour_to_points(cnt):
    return [(float(p[0][0]), float(p[0][1])) for p in cnt]