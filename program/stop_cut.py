#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import sys

MOONRAKER_URL = "http://127.0.0.1:7125"


def moonraker_get(endpoint: str):
    url = f"{MOONRAKER_URL}{endpoint}"
    with urllib.request.urlopen(url, timeout=10) as response:
        data = response.read().decode("utf-8")
        return json.loads(data)


def moonraker_post(endpoint: str, payload: dict | None = None):
    if payload is None:
        payload = {}

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


def get_print_state():
    """
    Hentar faktisk jobbstat frå print_stats.
    Dette er mykje meir påliteleg enn printer/info når vi vil vite
    om ei filkøyring er aktiv.
    """
    result = moonraker_get("/printer/objects/query?print_stats")
    return result["result"]["status"]["print_stats"]["state"]


def main():
    try:
        print_state = get_print_state()
        print(f"print_stats.state: {print_state}")

        if print_state.lower() not in ["printing", "paused"]:
            print("Det er ingen aktiv jobb å stoppe.")
            sys.exit(1)

        result = moonraker_post("/printer/print/cancel")

        print("Jobben vart stoppa.")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except urllib.error.HTTPError as e:
        print(f"HTTP-feil: {e.code} {e.reason}")
        try:
            print(e.read().decode())
        except Exception:
            pass
        sys.exit(1)

    except urllib.error.URLError as e:
        print("Klarte ikkje å kontakte Moonraker.")
        print(f"Feil: {e}")
        sys.exit(1)

    except KeyError as e:
        print(f"Fekk ikkje lese venta data frå Moonraker: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"Ukjent feil: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
