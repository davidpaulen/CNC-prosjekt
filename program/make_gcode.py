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

MM_PER_PIXEL = 1.0 / 11.0
SCALE_FACTOR = 15/11.6

OFFSET_X = 5.0
OFFSET_Y = 5.0

SAFE_Z = 10.0
CUT_Z = 1.8

FEED_Z = 600
FEED_TRAVEL = 3000

# =========================
# DRAG KNIFE / KOMPENSASJON
# =========================
# Start med 0.35 mm om du har vanleg liten drag knife.
# Dersom du VET at fysisk offset er 3 mm, kan du setje 3.0 her,
# men då må du forvente mykje større svingrørsler og dårlegare
# små detaljar.
KNIFE_OFFSET_MM = 0.35

# Svingar mindre enn dette får ikkje eigen swivel move.
CORNER_TOLERANCE_DEG = 20.0

# Kor tett vi resamplar punkt langs banen.
PATH_POINT_SPACING_MM = 0.35

# Kor mange linjesegment vi bruker for å lage swivel-bogen i hjørne.
SWIVEL_ARC_SEGMENTS = 12

# Små detaljar går saktare.
SMALL_PATH_PERIMETER_MM = 20.0
SMALL_RADIUS_MM = 3.0

FEED_XY_NORMAL = 1400
FEED_XY_SLOW = 500
FEED_XY_SWIVEL = 350

# Valfritt: liten Z-løft under skarpe swivel-rørsler.
# Sidan CUT_Z hos deg er 0, er det tryggast å starte utan dette.
USE_SWIVEL_LIFT = False
SWIVEL_Z = 0.2

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

    main_idx = max(external_indices, key=lambda i: cv2.contourArea(contours[i]))

    filtered = []
    filtered.append(contours[main_idx])

    for i, h in enumerate(hierarchy):
        parent = h[3]
        if parent == main_idx:
            cnt = contours[i]
            area = cv2.contourArea(cnt)

            if area < MIN_CONTOUR_AREA:
                continue

            filtered.append(cnt)

    filtered.sort(key=cv2.contourArea)
    return filtered


def smooth_contour(cnt):
    # For drag knife er det betre å halde på rå kontur
    # enn å polygonforenkle aggressivt.
    return cnt


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
        x_mm = OFFSET_X + x_px * MM_PER_PIXEL * SCALE_FACTOR
        y_mm = OFFSET_Y + (image_height - y_px) * MM_PER_PIXEL * SCALE_FACTOR
        transformed.append((x_mm, y_mm))

    return transformed


def distance(p1, p2):
    return float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))


def normalize(vx, vy):
    length = float(np.hypot(vx, vy))
    if length == 0:
        return 0.0, 0.0
    return vx / length, vy / length


def signed_turn_angle_deg(v1, v2):
    x1, y1 = normalize(v1[0], v1[1])
    x2, y2 = normalize(v2[0], v2[1])

    dot = np.clip(x1 * x2 + y1 * y2, -1.0, 1.0)
    cross = x1 * y2 - y1 * x2

    angle = np.degrees(np.arctan2(cross, dot))
    return float(angle)


def resample_closed_path(points, spacing):
    if len(points) < 3:
        return points[:]

    pts = points[:]
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    new_points = [pts[0]]

    for i in range(len(pts) - 1):
        p1 = pts[i]
        p2 = pts[i + 1]
        seg_len = distance(p1, p2)

        if seg_len == 0:
            continue

        ux = (p2[0] - p1[0]) / seg_len
        uy = (p2[1] - p1[1]) / seg_len

        d = spacing
        while d < seg_len:
            nx = p1[0] + ux * d
            ny = p1[1] + uy * d
            new_points.append((nx, ny))
            d += spacing

        new_points.append(p2)

    if len(new_points) > 1 and distance(new_points[0], new_points[-1]) < 1e-9:
        new_points.pop()

    return new_points


def polygon_perimeter(points):
    if len(points) < 2:
        return 0.0

    total = 0.0
    for i in range(len(points)):
        total += distance(points[i], points[(i + 1) % len(points)])
    return total


def estimate_min_radius(points):
    if len(points) < 3:
        return 999999.0

    radii = []

    for i in range(len(points)):
        p0 = np.array(points[i - 1], dtype=float)
        p1 = np.array(points[i], dtype=float)
        p2 = np.array(points[(i + 1) % len(points)], dtype=float)

        a = np.linalg.norm(p1 - p0)
        b = np.linalg.norm(p2 - p1)
        c = np.linalg.norm(p2 - p0)

        if a < 1e-9 or b < 1e-9 or c < 1e-9:
            continue

        area2 = abs(np.cross(p1 - p0, p2 - p0))
        if area2 < 1e-9:
            continue

        radius = (a * b * c) / (2.0 * area2)
        radii.append(radius)

    if not radii:
        return 999999.0

    return float(min(radii))


def classify_path(points):
    perim = polygon_perimeter(points)
    min_r = estimate_min_radius(points)

    is_small = (perim <= SMALL_PATH_PERIMETER_MM) or (min_r <= SMALL_RADIUS_MM)

    return {
        "perimeter_mm": perim,
        "min_radius_mm": min_r,
        "is_small": is_small
    }


def build_dragknife_path(points, knife_offset, tolerance_deg, arc_segments):
    """
    Bygg kompensert bane for drag knife.
    """
    if len(points) < 3:
        return points[:]

    out = []
    n = len(points)

    for i in range(n):
        prev_p = points[i - 1]
        corner = points[i]
        next_p = points[(i + 1) % n]

        vin = (corner[0] - prev_p[0], corner[1] - prev_p[1])
        vout = (next_p[0] - corner[0], next_p[1] - corner[1])

        in_len = np.hypot(vin[0], vin[1])
        out_len = np.hypot(vout[0], vout[1])

        if in_len < 1e-9 or out_len < 1e-9:
            if not out or distance(out[-1], corner) > 1e-9:
                out.append(corner)
            continue

        uin = normalize(vin[0], vin[1])
        uout = normalize(vout[0], vout[1])

        turn_deg = signed_turn_angle_deg(vin, vout)
        abs_turn = abs(turn_deg)

        local_offset = min(knife_offset, in_len * 0.45, out_len * 0.45)

        if abs_turn < tolerance_deg or local_offset < 1e-4:
            if not out or distance(out[-1], corner) > 1e-9:
                out.append(corner)
            continue

        p_before = (
            corner[0] - uin[0] * local_offset,
            corner[1] - uin[1] * local_offset
        )

        overshoot = (
            corner[0] + uin[0] * local_offset,
            corner[1] + uin[1] * local_offset
        )

        p_after = (
            corner[0] + uout[0] * local_offset,
            corner[1] + uout[1] * local_offset
        )

        if not out:
            out.append(p_before)
        else:
            if distance(out[-1], p_before) > 1e-9:
                out.append(p_before)

        if distance(out[-1], overshoot) > 1e-9:
            out.append(overshoot)

        start_ang = np.arctan2(overshoot[1] - corner[1], overshoot[0] - corner[0])
        end_ang = np.arctan2(p_after[1] - corner[1], p_after[0] - corner[0])

        if turn_deg > 0:
            while end_ang <= start_ang:
                end_ang += 2.0 * np.pi
        else:
            while end_ang >= start_ang:
                end_ang -= 2.0 * np.pi

        for j in range(1, arc_segments + 1):
            t = j / arc_segments
            ang = start_ang + (end_ang - start_ang) * t
            px = corner[0] + local_offset * np.cos(ang)
            py = corner[1] + local_offset * np.sin(ang)
            if distance(out[-1], (px, py)) > 1e-9:
                out.append((px, py))

    return out


def prepare_dragknife_paths(paths_mm):
    prepared = []

    for path in paths_mm:
        if len(path) < 3:
            continue

        resampled = resample_closed_path(path, PATH_POINT_SPACING_MM)
        compensated = build_dragknife_path(
            resampled,
            knife_offset=KNIFE_OFFSET_MM,
            tolerance_deg=CORNER_TOLERANCE_DEG,
            arc_segments=SWIVEL_ARC_SEGMENTS
        )
        info = classify_path(resampled)

        prepared.append({
            "original": path,
            "resampled": resampled,
            "compensated": compensated,
            "info": info
        })

    return prepared


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


def generate_gcode(prepared_paths):
    g = []

    g.append("; Pakning generert frå bilete")
    g.append("; Drag knife compensation aktiv")
    g.append("G21 ; mm")
    g.append("G90 ; absolute positioning")
    g.append("G28 ; home")
    g.append(f"G0 Z{SAFE_Z:.3f} F{FEED_Z}")

    for item in prepared_paths:
        path = item["compensated"]
        info = item["info"]

        if len(path) < 2:
            continue

        cut_feed = FEED_XY_SLOW if info["is_small"] else FEED_XY_NORMAL
        start_x, start_y = path[0]

        g.append("")
        g.append(
            f"; path perimeter={info['perimeter_mm']:.2f} mm, "
            f"min_radius={info['min_radius_mm']:.2f} mm, "
            f"small={info['is_small']}"
        )

        g.append(f"G0 X{start_x:.3f} Y{start_y:.3f} F{FEED_TRAVEL}")
        g.append(f"G1 Z{CUT_Z:.3f} F{FEED_Z}")

        prev_feed = None
        for i in range(3):
            for i in range(1, len(path)):
                x, y = path[i]

                feed = cut_feed

                # Litt ekstra ro rundt svært små steg / swivel-segment
                seg_len = distance(path[i - 1], path[i])
                if seg_len <= max(KNIFE_OFFSET_MM * 0.6, PATH_POINT_SPACING_MM * 1.2):
                    feed = min(feed, FEED_XY_SWIVEL)

                if USE_SWIVEL_LIFT and feed == FEED_XY_SWIVEL:
                    g.append(f"G1 Z{SWIVEL_Z:.3f} F{FEED_Z}")
                    g.append(f"G1 X{x:.3f} Y{y:.3f} F{feed}")
                    g.append(f"G1 Z{CUT_Z:.3f} F{FEED_Z}")
                else:
                    g.append(f"G1 X{x:.3f} Y{y:.3f} F{feed}")

                prev_feed = feed

        g.append(f"G1 X{start_x:.3f} Y{start_y:.3f} F{cut_feed}")
        g.append(f"G0 Z{SAFE_Z:.3f} F{FEED_Z}")

    g.append("")
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
    lines.append(f"SCALE_FACTOR = {SCALE_FACTOR}")
    lines.append(f"OFFSET_X = {OFFSET_X}")
    lines.append(f"OFFSET_Y = {OFFSET_Y}")
    lines.append(f"KNIFE_OFFSET_MM = {KNIFE_OFFSET_MM}")
    lines.append(f"CORNER_TOLERANCE_DEG = {CORNER_TOLERANCE_DEG}")
    lines.append(f"PATH_POINT_SPACING_MM = {PATH_POINT_SPACING_MM}")
    lines.append(f"SWIVEL_ARC_SEGMENTS = {SWIVEL_ARC_SEGMENTS}")
    lines.append(f"FEED_XY_NORMAL = {FEED_XY_NORMAL}")
    lines.append(f"FEED_XY_SLOW = {FEED_XY_SLOW}")
    lines.append(f"FEED_XY_SWIVEL = {FEED_XY_SWIVEL}")
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

    paths_mm = normalize_paths_to_origin(paths_mm, OFFSET_X, OFFSET_Y)

    status("KOMPENSERER FOR DRAG KNIFE")
    prepared_paths = prepare_dragknife_paths(paths_mm)

    compensated = [p["compensated"] for p in prepared_paths]
    check_bounds(compensated)

    status("LAGRAR DEBUG")
    save_debug_images(img, cropped, gray, binary, contours, smoothed_contours)
    save_debug_info(img.shape, cropped.shape, roi_rect, contours, smoothed_contours, compensated)

    status("SKRIV G-KODE")
    gcode_text = generate_gcode(prepared_paths)
    OUTPUT_GCODE.write_text(gcode_text, encoding="utf-8")

    if not OUTPUT_GCODE.exists():
        fail("Klarte ikkje lagre G-kode")

    status("FERDIG")


if __name__ == "__main__":
    main()
