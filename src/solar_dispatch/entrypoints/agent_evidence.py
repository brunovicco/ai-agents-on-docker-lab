"""Gate a Docker Agent proposal on evidence that the agent read the forecast through its tool.

Reads the newline-delimited JSON transcript of `docker agent run --exec --json` from stdin.
The final answer is the last structured output, if the agent produced one, or else the text the
agent wrote after its last tool result. The gate accepts only when a `forecast_day` call precedes
that answer, then writes the answer as the proposal for `dispatch verify`. The verifier checks
the result; this gate checks the process, so a correct guess made without reading the forecast is
rejected.
"""

import argparse
import json
import sys
from dataclasses import dataclass

from solar_dispatch.entrypoints.dispatch import load_strict_json

MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024
OUTPUT_TOOL = "__structured_output__"
FORECAST_TOOL = "forecast_day"


@dataclass(frozen=True)
class _Event:
    kind: str
    tool: str = ""
    arguments: str = ""
    content: str = ""


def _events(transcript: bytes) -> list[_Event]:
    """Parse the transcript into the events the gate needs, in order."""
    events: list[_Event] = []
    for number, line in enumerate(transcript.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"Invalid transcript line {number}") from exc
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "tool_call":
            function = (event.get("tool_call") or {}).get("function") or {}
            name, arguments = function.get("name"), function.get("arguments", "")
            if not isinstance(name, str) or not isinstance(arguments, str):
                raise ValueError(f"Malformed tool call on transcript line {number}")
            events.append(_Event("tool_call", tool=name, arguments=arguments))
        elif kind == "tool_call_response":
            events.append(_Event("tool_call_response"))
        elif kind == "agent_choice" and isinstance(event.get("content"), str):
            events.append(_Event("agent_choice", content=event["content"]))
    return events


def _strip_fence(text: str) -> str:
    """Accept a single fenced code block around the answer, and nothing else."""
    text = text.strip()
    if text.startswith("```") and text.endswith("```") and text.count("```") == 2:
        body = text[3:-3]
        return body.removeprefix("json").strip()
    return text


def proposal_from_transcript(transcript: bytes) -> object:
    """Return the final answer if the forecast tool was called before it."""
    events = _events(transcript)
    outputs = [i for i, e in enumerate(events) if e.kind == "tool_call" and e.tool == OUTPUT_TOOL]
    if outputs:
        final, answer = outputs[-1], events[outputs[-1]].arguments
    else:
        boundary = max(
            (i for i, e in enumerate(events) if e.kind == "tool_call_response"), default=-1
        )
        answer = "".join(e.content for e in events[boundary + 1 :] if e.kind == "agent_choice")
        if not answer.strip():
            raise ValueError("The agent produced no final answer")
        final = boundary + 1
    called = any(e.kind == "tool_call" and e.tool.endswith(FORECAST_TOOL) for e in events[:final])
    if not called:
        raise ValueError("The agent answered without reading the forecast through forecast_day")
    return load_strict_json(_strip_fence(answer))


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
