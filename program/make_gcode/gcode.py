from .config import *


def generate_gcode(paths):
    g = []
    g.append("G21")

    for item in paths:
        path = item["compensated"]

        if not path:
            continue

        x0,y0 = path[0]
        g.append(f"G0 X{x0:.2f} Y{y0:.2f}")

        for x,y in path:
            g.append(f"G1 X{x:.2f} Y{y:.2f}")

    return "\n".join(g)