"""Gate a Docker Agent proposal on evidence that the agent read the forecast through its tool.

Reads the newline-delimited JSON transcript of `docker agent run --exec --json` from stdin.
Accepts only when a `forecast_day` tool call precedes the final structured output, then writes
that output as the proposal for `dispatch verify`. The verifier checks the result; this gate
checks the process, so a correct guess made without reading the forecast is rejected.
"""

import argparse
import json
import sys

from solar_dispatch.entrypoints.dispatch import load_strict_json

MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024
OUTPUT_TOOL = "__structured_output__"
FORECAST_TOOL = "forecast_day"


def _tool_calls(transcript: bytes) -> list[tuple[str, str]]:
    """Return (name, arguments) for each tool call event in transcript order."""
    calls: list[tuple[str, str]] = []
    for number, line in enumerate(transcript.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"Invalid transcript line {number}") from exc
        if not isinstance(event, dict) or event.get("type") != "tool_call":
            continue
        function = (event.get("tool_call") or {}).get("function") or {}
        name, arguments = function.get("name"), function.get("arguments", "")
        if not isinstance(name, str) or not isinstance(arguments, str):
            raise ValueError(f"Malformed tool call on transcript line {number}")
        calls.append((name, arguments))
    return calls


def proposal_from_transcript(transcript: bytes) -> object:
    """Return the final structured output if the forecast tool was called before it."""
    calls = _tool_calls(transcript)
    outputs = [index for index, (name, _) in enumerate(calls) if name == OUTPUT_TOOL]
    if not outputs:
        raise ValueError("The agent produced no structured output")
    final = outputs[-1]
    if not any(name.endswith(FORECAST_TOOL) for name, _ in calls[:final]):
        raise ValueError("The agent answered without reading the forecast through forecast_day")
    return load_strict_json(calls[final][1])


def main() -> None:
    """Run the evidence gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        transcript = sys.stdin.buffer.read(MAX_TRANSCRIPT_BYTES + 1)
        if len(transcript) > MAX_TRANSCRIPT_BYTES:
            raise ValueError("Transcript exceeds 64 MiB")
        print(json.dumps(proposal_from_transcript(transcript)))
    except ValueError as exc:
        parser.exit(1, f"Rejected: {exc}\n")


if __name__ == "__main__":
    main()
