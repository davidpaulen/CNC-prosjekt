from pathlib import Path
import shutil
import sys
import subprocess


def finn_usb_mappe():
    """
    Prøver å finne første tilgjengelege USB-minnepinne under:
    /media/david/
    eller /media/pi/
    """
    moglege_roter = [Path("/media/david"), Path("/media/pi")]

    for rot in moglege_roter:
        if rot.exists() and rot.is_dir():
            undermapper = [m for m in rot.iterdir() if m.is_dir()]
            if undermapper:
                return undermapper[0]

    return None


def hovud():
    prosjektrot = Path(__file__).resolve().parent.parent
    kjelde_fil = prosjektrot / "data" / "pakking.gcode"

    if not kjelde_fil.exists():
        print(f"Feil: Fann ikkje gkodefila: {kjelde_fil}")
        sys.exit(1)

    usb_mappe = finn_usb_mappe()

    if usb_mappe is None:
        print("Feil: Fann ingen minnepinne under /media/david/ eller /media/pi/")
        print("Sjekk at minnepinnen er sett inn og montert.")
        sys.exit(1)

    mål_fil = usb_mappe / kjelde_fil.name

    try:
        shutil.copy2(kjelde_fil, mål_fil)
        print(f"Gkodefila vart kopiert til: {mål_fil}")

        # Sørgjer for at alle data blir skrivne ferdig til disken
        subprocess.run(["sync"], check=True)

        # Avmonterer minnepinnen automatisk
        subprocess.run(["umount", str(usb_mappe)], check=True)

        print(f"USB-minnepinnen er no trygt løyst ut: {usb_mappe}")
        print("No kan du dra ut minnepinnen.")
    except subprocess.CalledProcessError as e:
        print(f"Feil ved systemkommando: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Feil ved kopiering: {e}")
        sys.exit(1)


if __name__ == "__main__":
    hovud()
