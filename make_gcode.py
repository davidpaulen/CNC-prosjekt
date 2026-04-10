import cv2
import numpy as np
import sys
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PROGRAM_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

INPUT_IMAGE = DATA_DIR / "pakking.jpg"
OUTPUT_GCODE = DATA_DIR / "pakking.gcode"

DEBUG_CROPPED = DATA_DIR / "debug_cropped.png"
DEBUG_GRAY = DATA_DIR / "debug_gray.png"
DEBUG_BINARY = DATA_DIR / "debug_binary.png"
DEBUG_RAW_CONTOURS = DATA_DIR / "debug_raw_contours.png"
DEBUG_SMOOTH_CONTOURS = DATA_DIR / "debug_smooth_contours.png"
DEBUG_INFO = DATA_DIR / "debug_info.txt"

# =========================
# ROI / UTSNITT
# =========================
# Berre dette området av biletet blir brukt.
# Start med heile biletet eller eit grovt område, og juster etterpå.
ROI_X = 970
ROI_Y = 170
ROI_W = 2680
ROI_H = 2250

USE_ROI = True

# =========================
# MASKIN / KALIBRERING
# =========================
BED_WIDTH_MM = 250.0
BED_HEIGHT_MM = 210.0

MM_PER_PIXEL = 1.0/11.0

OFFSET_X = 20.0
OFFSET_Y = 20.0

SAFE_Z = 10.0
CUT_Z = 0

FEED_XY = 1800
FEED_Z = 600
FEED_TRAVEL = 3000

# =========================
# BILETBEHANDLING
# =========================
BLUR_SIZE = 10

# "fixed", "otsu", "adaptive"
THRESHOLD_MODE = "otsu"
THRESHOLD_VALUE = 120

MORPH_KERNEL_SIZE = 5
USE_MORPH_OPEN = True
USE_MORPH_CLOSE = True

# =========================
# KONTURAR
# =========================
MIN_CONTOUR_AREA = 50
APPROX_EPSILON_FACTOR = 0.0015
ONLY_LARGEST_CONTOUR = False

REJECT_BORDER_CONTOURS = True
BORDER_MARGIN_PX = 3


def status(msg):
    print(f"STATUS:{msg}", flush=True)


def fail(msg):
    print(f"FEIL: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def ensure_odd(value):
    if value % 2 == 0:
        value += 1
    return max(1, value)


def load_image(path):
    img = cv2.imread(str(path))
    if img is None:
        fail(f"Fann ikkje bilete: {path}")
    return img


def crop_roi(img):
    h, w = img.shape[:2]

    if not USE_ROI:
        return img.copy(), (0, 0, w, h)

    x = max(0, ROI_X)
    y = max(0, ROI_Y)
    roi_w = max(1, ROI_W)
    roi_h = max(1, ROI_H)

    x2 = min(w, x + roi_w)
    y2 = min(h, y + roi_h)

    if x >= x2 or y >= y2:
        fail("ROI er ugyldig")

    cropped = img[y:y2, x:x2].copy()
    return cropped, (x, y, x2 - x, y2 - y)


def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur_size = ensure_odd(BLUR_SIZE)
    blur = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)

    if THRESHOLD_MODE == "fixed":
        _, binary = cv2.threshold(
            blur,
            THRESHOLD_VALUE,
            255,
            cv2.THRESH_BINARY
        )

    elif THRESHOLD_MODE == "otsu":
        _, binary = cv2.threshold(
            blur,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

    elif THRESHOLD_MODE == "adaptive":
        block_size = 31
        if block_size % 2 == 0:
            block_size += 1

        binary = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            8
        )
    else:
        fail(f"Ukjend THRESHOLD_MODE: {THRESHOLD_MODE}")

    kernel_size = max(1, MORPH_KERNEL_SIZE)
    kernel = np.ones((kernel_size, kernel_size), np.uint8)

    if USE_MORPH_OPEN:
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    if USE_MORPH_CLOSE:
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Behald berre største kvite samanhengande objekt
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    if num_labels > 1:
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        cleaned = np.zeros_like(binary)
        cleaned[labels == largest_label] = 255
        binary = cleaned

    return gray, binary


def touches_border(cnt, width, height, margin=0):
    x, y, w, h = cv2.boundingRect(cnt)

    if x <= margin:
        return True
    if y <= margin:
        return True
    if x + w >= width - margin:
        return True
    if y + h >= height - margin:
        return True

    return False


def find_valid_contours(binary_img):
    height, width = binary_img.shape[:2]

    contours, hierarchy = cv2.findContours(
        binary_img,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_NONE
    )

    if hierarchy is None or len(contours) == 0:
        fail("Fann ingen konturar")

    hierarchy = hierarchy[0]

    # Finn berre ytre konturar først (parent = -1)
    external_indices = []
    for i, h in enumerate(hierarchy):
        parent = h[3]
        if parent == -1:
            cnt = contours[i]
            area = cv2.contourArea(cnt)

            if area < MIN_CONTOUR_AREA:
                continue

            if REJECT_BORDER_CONTOURS and touches_border(cnt, width, height, BORDER_MARGIN_PX):
                continue

            external_indices.append(i)

    if not external_indices:
        fail("Fann ingen gyldige ytre konturar")

    # Vel største ytre objekt
    main_idx = max(external_indices, key=lambda i: cv2.contourArea(contours[i]))

    filtered = []

    # Ta med sjølve ytterkonturen
    filtered.append(contours[main_idx])

    # Ta med barn av denne konturen (hol i pakninga)
    for i, h in enumerate(hierarchy):
        parent = h[3]
        if parent == main_idx:
            cnt = contours[i]
            area = cv2.contourArea(cnt)

            if area < MIN_CONTOUR_AREA:
                continue

            filtered.append(cnt)

    # Små først, stor utside sist
    filtered.sort(key=cv2.contourArea)

    return filtered


def smooth_contour(cnt):
    epsilon = APPROX_EPSILON_FACTOR * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    return approx


def contour_to_points(cnt):
    pts = []
    for p in cnt:
        x = float(p[0][0])
        y = float(p[0][1])
        pts.append((x, y))
    return pts


def transform_points_to_mm(points, image_height):
    transformed = []

    for x_px, y_px in points:
        x_mm = OFFSET_X + x_px * MM_PER_PIXEL
        y_mm = OFFSET_Y + (image_height - y_px) * MM_PER_PIXEL
        transformed.append((x_mm, y_mm))

    return transformed


def check_bounds(all_paths):
    for path in all_paths:
        for x, y in path:
            if x < 0 or x > BED_WIDTH_MM:
                fail(f"X utanfor seng: {x:.2f} mm")
            if y < 0 or y > BED_HEIGHT_MM:
                fail(f"Y utanfor seng: {y:.2f} mm")


def save_debug_images(original_img, cropped_img, gray_img, binary_img, raw_contours, smooth_contours):
    cv2.imwrite(str(DEBUG_CROPPED), cropped_img)
    cv2.imwrite(str(DEBUG_GRAY), gray_img)
    cv2.imwrite(str(DEBUG_BINARY), binary_img)

    raw_dbg = cropped_img.copy()
    cv2.drawContours(raw_dbg, raw_contours, -1, (0, 255, 0), 2)
    cv2.imwrite(str(DEBUG_RAW_CONTOURS), raw_dbg)

    smooth_dbg = cropped_img.copy()
    cv2.drawContours(smooth_dbg, smooth_contours, -1, (0, 255, 0), 2)
    cv2.imwrite(str(DEBUG_SMOOTH_CONTOURS), smooth_dbg)


def generate_gcode(paths):
    g = []

    g.append("; Pakning generert frå bilete")
    g.append("G21 ; mm")
    g.append("G90 ; absolute positioning")
    g.append("G28 ; home")
    g.append(f"G0 Z{SAFE_Z:.3f} F{FEED_Z}")

    for path in paths:
        if len(path) < 2:
            continue

        start_x, start_y = path[0]

        g.append(f"G0 X{start_x:.3f} Y{start_y:.3f} F{FEED_TRAVEL}")
        g.append(f"G1 Z{CUT_Z:.3f} F{FEED_Z}")

        for x, y in path[1:]:
            g.append(f"G1 X{x:.3f} Y{y:.3f} F{FEED_XY}")

        g.append(f"G1 X{start_x:.3f} Y{start_y:.3f} F{FEED_XY}")
        g.append(f"G0 Z{SAFE_Z:.3f} F{FEED_Z}")

    g.append(f"G0 X0 Y0 F{FEED_TRAVEL}")
    g.append("M84 ; motors off")

    return "\n".join(g) + "\n"


def save_debug_info(
    original_shape,
    cropped_shape,
    roi_rect,
    contours,
    smoothed_contours,
    paths_mm
):
    lines = []

    lines.append("DEBUG INFO")
    lines.append("=" * 40)
    lines.append(f"Input image: {INPUT_IMAGE.name}")
    lines.append(f"Original size: {original_shape[1]} x {original_shape[0]} px")
    lines.append(f"Cropped size:  {cropped_shape[1]} x {cropped_shape[0]} px")
    lines.append(f"ROI used: x={roi_rect[0]}, y={roi_rect[1]}, w={roi_rect[2]}, h={roi_rect[3]}")
    lines.append("")
    lines.append("PARAMETER")
    lines.append("-" * 40)
    lines.append(f"THRESHOLD_MODE = {THRESHOLD_MODE}")
    lines.append(f"THRESHOLD_VALUE = {THRESHOLD_VALUE}")
    lines.append(f"BLUR_SIZE = {BLUR_SIZE}")
    lines.append(f"MORPH_KERNEL_SIZE = {MORPH_KERNEL_SIZE}")
    lines.append(f"USE_MORPH_OPEN = {USE_MORPH_OPEN}")
    lines.append(f"USE_MORPH_CLOSE = {USE_MORPH_CLOSE}")
    lines.append(f"MIN_CONTOUR_AREA = {MIN_CONTOUR_AREA}")
    lines.append(f"APPROX_EPSILON_FACTOR = {APPROX_EPSILON_FACTOR}")
    lines.append(f"ONLY_LARGEST_CONTOUR = {ONLY_LARGEST_CONTOUR}")
    lines.append(f"MM_PER_PIXEL = {MM_PER_PIXEL}")
    lines.append(f"OFFSET_X = {OFFSET_X}")
    lines.append(f"OFFSET_Y = {OFFSET_Y}")
    lines.append("")
    lines.append("KONTURAR")
    lines.append("-" * 40)
    lines.append(f"Tal konturar: {len(contours)}")

    for i, cnt in enumerate(contours, start=1):
        area = cv2.contourArea(cnt)
        perimeter = cv2.arcLength(cnt, True)
        raw_points = len(cnt)
        smooth_points = len(smoothed_contours[i - 1])
        x, y, w, h = cv2.boundingRect(cnt)

        lines.append(
            f"{i}: area={area:.1f}, perimeter={perimeter:.1f}, "
            f"raw_pts={raw_points}, smooth_pts={smooth_points}, "
            f"bbox=({x},{y},{w},{h})"
        )

    lines.append("")
    lines.append("BANER I MM")
    lines.append("-" * 40)

    for i, path in enumerate(paths_mm, start=1):
        if not path:
            continue

        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        lines.append(
            f"{i}: pts={len(path)}, "
            f"x=[{min(xs):.2f}, {max(xs):.2f}], "
            f"y=[{min(ys):.2f}, {max(ys):.2f}]"
        )

    DEBUG_INFO.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    status("LES BILDE")
    img = load_image(INPUT_IMAGE)

    status("CROPPAR ROI")
    cropped, roi_rect = crop_roi(img)

    status("BEHANDLAR BILDE")
    gray, binary = preprocess_image(cropped)

    status("FINN KONTOURAR")
    contours = find_valid_contours(binary)

    status("GLATTAR KONTOURAR")
    smoothed_contours = [smooth_contour(c) for c in contours]

    status("LAGAR BANER")
    image_height = cropped.shape[0]

    paths_mm = []
    for cnt in smoothed_contours:
        pts_px = contour_to_points(cnt)
        pts_mm = transform_points_to_mm(pts_px, image_height)
        paths_mm.append(pts_mm)

    check_bounds(paths_mm)

    status("LAGRAR DEBUG")
    save_debug_images(img, cropped, gray, binary, contours, smoothed_contours)
    save_debug_info(img.shape, cropped.shape, roi_rect, contours, smoothed_contours, paths_mm)

    status("SKRIV G-KODE")
    gcode_text = generate_gcode(paths_mm)
    OUTPUT_GCODE.write_text(gcode_text, encoding="utf-8")

    if not OUTPUT_GCODE.exists() or OUTPUT_GCODE.stat().st_size == 0:
        fail("Klarte ikkje å lagre G-kode")

    status("FERDIG")
    print(f"Laga: {OUTPUT_GCODE.name}")
    print(f"Laga: {DEBUG_CROPPED.name}")
    print(f"Laga: {DEBUG_GRAY.name}")
    print(f"Laga: {DEBUG_BINARY.name}")
    print(f"Laga: {DEBUG_RAW_CONTOURS.name}")
    print(f"Laga: {DEBUG_SMOOTH_CONTOURS.name}")
    print(f"Laga: {DEBUG_INFO.name}")


if __name__ == "__main__":
    main()
