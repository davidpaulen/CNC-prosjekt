import sys

def status(msg):
    print(f"STATUS:{msg}", flush=True)

def fail(msg):
    print(f"FEIL: {msg}", file=sys.stderr)
    sys.exit(1)

def ensure_odd(x):
    return x if x % 2 else x + 1