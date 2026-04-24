import cv2
import numpy as np

from .config import *
from .utils import *


def load_image(path):
    img = cv2.imread(str(path))
    if img is None:
        fail("Fann ikkje bilete")
    return img


def crop_roi(img):
    if not USE_ROI:
        return img, (0,0,0,0)

    return img[ROI_Y:ROI_Y+ROI_H, ROI_X:ROI_X+ROI_W], (ROI_X, ROI_Y, ROI_W, ROI_H)


def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (ensure_odd(BLUR_SIZE),)*2, 0)

    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return gray, binary