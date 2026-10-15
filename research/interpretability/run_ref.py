"""Run REF jobs for up to N seconds (default 150), from the project root."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seconds", nargs="?", type=float, default=150)
    args = parser.parse_args()
    if not 0 < args.seconds < float("inf"):
        parser.error("seconds must be finite and positive")

    missing = [name for name in ("requests", "pandas") if importlib.util.find_spec(name) is None]
    if missing:
        python = ROOT / ".venv/bin/python"
        if python.is_file() and Path(sys.prefix).resolve() != python.parent.parent.resolve():
            os.execv(str(python), [str(python), "-u", str(Path(__file__).resolve()), *sys.argv[1:]])
        parser.exit(1, "Missing Python packages: " + ", ".join(missing) + "\n"
                    "Install with: python3 -m venv .venv && "
                    ".venv/bin/python -m pip install -r scripts/composites/requirements.txt\n")

    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT / "scripts/composites"))
    import tq

    print(f"Running REF jobs for up to {args.seconds:g}s from {ROOT}", flush=True)
    try:
        tq.tick(args.seconds, exp="REF")
    finally:
        tq.report("REF")


if __name__ == "__main__":
    main()
