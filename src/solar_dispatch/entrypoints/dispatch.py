"""Propose a schedule or verify JSON from stdin against the operator's forecast."""

import argparse
import json
import sys
from pathlib import Path

from solar_dispatch.domain.dispatch import Forecast


def main() -> None:
    """Run the dispatch CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "verify"])
    parser.add_argument("forecast", type=Path)
    args = parser.parse_args()
    try:
        forecast = Forecast.parse(json.loads(args.forecast.read_text()))
        if args.command == "plan":
            print(json.dumps({"hours": forecast.propose()}))
            return
        raw = sys.stdin.buffer.read(4097)
        if len(raw) > 4096:
            raise ValueError("Proposal exceeds 4 KiB")
        candidate = json.loads(raw)
        if not isinstance(candidate, dict) or set(candidate) != {"hours"}:
            raise ValueError("Invalid proposal format")
        grid_wh = forecast.verify(candidate["hours"])
        print(json.dumps({"decision": "accepted", "hours": candidate["hours"], "grid_wh": grid_wh}))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Rejected: {exc}\n")


if __name__ == "__main__":
    main()
