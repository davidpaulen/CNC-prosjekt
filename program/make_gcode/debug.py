import cv2
from .config import *


def save_debug_images(img, crop, gray, bin, raw, smooth):
    cv2.imwrite(str(DEBUG_CROPPED), crop)
    cv2.imwrite(str(DEBUG_GRAY), gray)
    cv2.imwrite(str(DEBUG_BINARY), bin)


def save_debug_info(*args):
    DEBUG_INFO.write_text("debug")