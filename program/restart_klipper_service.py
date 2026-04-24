import subprocess
import sys
import time


def status(msg):
    print(f"STATUS:{msg}", flush=True)


def done():
    print("DONE:RESTART_KLIPPER_SERVICE", flush=True)


def error(msg):
    print(f"ERROR:RESTART_KLIPPER_SERVICE:{msg}", flush=True)
    sys.exit(1)


def main():
    try:
        status("STOPPAR KLIPPER")

        subprocess.run(
            ["sudo", "systemctl", "restart", "klipper.service"],
            check=True
        )

        # Litt venting så den får starte opp skikkeleg
        time.sleep(2)

        status("STARTAR OPP")

        # Sjekk status
        result = subprocess.run(
            ["systemctl", "is-active", "klipper.service"],
            capture_output=True,
            text=True
        )

        if result.stdout.strip() != "active":
            error("KLIPPER STARTA IKKJE")

        status("FERDIG")
        done()

    except subprocess.CalledProcessError as e:
        error("FEIL VED RESTART")


if __name__ == "__main__":
    main()
