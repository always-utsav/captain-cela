"""Launch the CAPTAIN Trace Explorer.

Usage::

    python scripts/launch_explorer.py
    python scripts/launch_explorer.py --port 8080
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from captain.explorer.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="CAPTAIN Trace Explorer")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--store", default=None, help="Trace store directory")
    args = parser.parse_args()

    store_dir = Path(args.store) if args.store else None
    app = create_app(store_dir=store_dir)

    print(f"CAPTAIN Trace Explorer: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
