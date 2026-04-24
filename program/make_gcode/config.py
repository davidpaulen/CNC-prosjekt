from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROGRAM_DIR / "data"

INPUT_IMAGE = DATA_DIR / "pakking.jpg"
OUTPUT_GCODE = DATA_DIR / "pakking.gcode"

DEBUG_CROPPED = DATA_DIR / "debug_cropped.png"
DEBUG_GRAY = DATA_DIR / "debug_gray.png"
DEBUG_BINARY = DATA_DIR / "debug_binary.png"
DEBUG_RAW_CONTOURS = DATA_DIR / "debug_raw.png"
DEBUG_SMOOTH_CONTOURS = DATA_DIR / "debug_smooth.png"
DEBUG_INFO = DATA_DIR / "debug.txt"

USE_ROI = True
ROI_X, ROI_Y, ROI_W, ROI_H = 970, 170, 2680, 2250

MM_PER_PIXEL = 1/11
SCALE_FACTOR = 15/11.6

# Dissa kan endrast utifrå kor langt ifrå kanten pakninga skal bli kutta
OFFSET_X = 20
OFFSET_Y = 50

KNIFE_OFFSET_MM = 3
CORNER_TOLERANCE_DEG = 20
PATH_POINT_SPACING_MM = 0.35
SWIVEL_ARC_SEGMENTS = 12

BED_WIDTH_MM = 250
BED_HEIGHT_MM = 210

BLUR_SIZE = 10
THRESHOLD_MODE = "otsu"
MORPH_KERNEL_SIZE = 5

MIN_CONTOUR_AREA = 50