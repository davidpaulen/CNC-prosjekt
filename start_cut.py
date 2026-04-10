#!/usr/bin/env python3
import os
import sys
import json
import shutil
import urllib.request
import urllib.parse
from pathlib import Path

# =========================
# INNSTILLINGAR
# =========================
SOURCE_DIR = Path("/home/david/Prosjekt/CNCprosjekt/data")
KLIPPER_GCODES_DIR = Path("/home/david/printer_data/gcodes")
MOONRAKER_URL = "http://127.0.0.1:7125"

VALID_EXTENSIONS = [".gcode", ".gc", ".gco", ".ngc"]


# =========================
# HJELPEFUNKSJONAR
# =========================
def moonraker_get(endpoint: str):
    url = f"{MOONRAKER_URL}{endpoint}"
    with urllib.request.urlopen(url, timeout=10) as response:
        data = response.read().decode("utf-8")
        return json.loads(data)


def moonraker_post(endpoint: str, payload: dict):
    url = f"{MOONRAKER_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        resp_data = response.read().decode("utf-8")
        return json.loads(resp_data)


def find_latest_gcode_file(source_dir: Path) -> Path | None:
    files = [
        f for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
    ]

    if not files:
        return None

    return max(files, key=lambda f: f.stat().st_mtime)


def find_named_gcode_file(source_dir: Path, filename: str) -> Path | None:
    candidate = source_dir / filename
    if candidate.exists() and candidate.is_file():
        return candidate

    # Dersom brukaren skriv utan ending, prøv å finne ei som matchar
    for ext in VALID_EXTENSIONS:
        candidate = source_dir / f"{filename}{ext}"
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def ensure_directories():
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Kjelde-mappa finst ikkje: {SOURCE_DIR}")

    if not KLIPPER_GCODES_DIR.exists():
        raise FileNotFoundError(f"Klipper gcodes-mappa finst ikkje: {KLIPPER_GCODES_DIR}")


def copy_to_klipper(source_file: Path) -> Path:
    destination_file = KLIPPER_GCODES_DIR / source_file.name
    shutil.copy2(source_file, destination_file)
    return destination_file


def get_printer_state():
    try:
        result = moonraker_get("/printer/info")
        return result.get("result", {}).get("state", "unknown")
    except Exception:
        return "unknown"


def start_print_in_klipper(gcode_file: Path):
    # Moonraker forventar filnamn relativt til printer_data/gcodes
    relative_name = gcode_file.relative_to(KLIPPER_GCODES_DIR).as_posix()
    return moonraker_post("/printer/print/start", {"filename": relative_name})


# =========================
# HOVUDPROGRAM
# =========================
def main():
    try:
        ensure_directories()

        # Dersom du køyrer:
        # python3 start_cut.py filnamn.gcode
        # så brukar han den fila.
        if len(sys.argv) > 1:
            wanted_name = sys.argv[1]
            source_file = find_named_gcode_file(SOURCE_DIR, wanted_name)

            if source_file is None:
                print(f"Fann ikkje fila '{wanted_name}' i {SOURCE_DIR}")
                sys.exit(1)
        else:
            # Elles vel han den nyaste gcode-fila automatisk
            source_file = find_latest_gcode_file(SOURCE_DIR)

            if source_file is None:
                print(f"Fann ingen gcode-filer i {SOURCE_DIR}")
                sys.exit(1)

        printer_state = get_printer_state()
        print(f"Printer state: {printer_state}")

        if printer_state.lower() not in ["ready", "idle", "standby", "unknown"]:
            print("Printeren ser ikkje ut til å vere klar for ny jobb.")
            print("Avbryt utskrifta manuelt først dersom noko allereie køyrer.")
            sys.exit(1)

        copied_file = copy_to_klipper(source_file)
        print(f"Kopierte fil til Klipper: {copied_file}")

        result = start_print_in_klipper(copied_file)
        print("Startkommando sendt til Klipper/Moonraker.")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except urllib.error.HTTPError as e:
        print(f"HTTP-feil frå Moonraker: {e.code} {e.reason}")
        try:
            print(e.read().decode())
        except Exception:
            pass
        sys.exit(1)

    except urllib.error.URLError as e:
        print("Klarte ikkje å kontakte Moonraker/Klipper.")
        print(f"Feil: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"Feil: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
