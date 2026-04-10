import subprocess
import sys
from pathlib import Path
import os

DATA_DIR = Path("/home/david/Prosjekt/CNCprosjekt/data")
OUTPUT_FILE = DATA_DIR / "pakking.jpg"
RPICAM = "/usr/bin/rpicam-still"


def status(msg):
    print(f"STATUS:{msg}", flush=True)


def fail(msg):
    print(msg, file=sys.stderr, flush=True)
    sys.exit(1)


def remove_old_file(path):
    if path.exists():
        try:
            # Gjer fila skrivbar viss ho er read-only
            os.chmod(path, 0o644)
        except Exception:
            pass

        try:
            path.unlink()
        except Exception as e:
            fail(f"Klarte ikkje å slette gammal bildefil: {e}")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    status("KLARGJER BILDE")
    remove_old_file(OUTPUT_FILE)

    status("STARTAR KAMERA")

    cmd = [
        RPICAM,
        "-n",
        "-o", str(OUTPUT_FILE),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
    except FileNotFoundError:
        fail("Fann ikkje rpicam-still")
    except Exception as e:
        fail(f"Klarte ikkje å starte kamera: {e}")

    if result.returncode != 0:
        error_text = (result.stderr or result.stdout or "").strip()

        if not error_text:
            error_text = "Ukjend kamerafeil"

        fail(error_text)

    if not OUTPUT_FILE.exists():
        fail("Biletfila vart ikkje laga")

    if OUTPUT_FILE.stat().st_size == 0:
        fail("Biletfila er tom")

    status("BILDE LAGRA")


if __name__ == "__main__":
    main()
