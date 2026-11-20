import io
import json
import sys

import pytest

from solar_dispatch.entrypoints.agent_evidence import main, proposal_from_transcript


def event(kind: str, **fields: object) -> str:
    return json.dumps({"type": kind, "agent_name": "root", **fields})


def call(name: str, arguments: str = "{}") -> str:
    return event("tool_call", tool_call={"function": {"name": name, "arguments": arguments}})


ANSWER = '{"hours": [10, 11]}'


def transcript(*lines: str) -> bytes:
    return ("\n".join([event("stream_started"), *lines, event("stream_stopped")]) + "\n").encode()


def test_accepts_answer_after_reading_the_forecast() -> None:
    lines = transcript(
        event("agent_choice_reasoning", content="thinking"),
        call("forecast_day"),
        event("tool_call_response", tool_call_id="1"),
        call("__structured_output__", ANSWER),
    )
    assert proposal_from_transcript(lines) == {"hours": [10, 11]}


def test_uses_the_last_structured_output_after_a_retry() -> None:
    lines = transcript(
        call("forecast_day"),
        call("__structured_output__", '{"hours": [12]}'),
        call("__structured_output__", ANSWER),
    )
    assert proposal_from_transcript(lines) == {"hours": [10, 11]}


def choice(text: str) -> str:
    return event("agent_choice", content=text)


def test_accepts_a_text_answer_written_after_the_tool_result() -> None:
    lines = transcript(
        choice("Let me read the forecast."),
        call("forecast_day"),
        event("tool_call_response", tool_call_id="1"),
        choice('{"hours": '),
        choice("[10, 11]}"),
    )
    assert proposal_from_transcript(lines) == {"hours": [10, 11]}


def test_accepts_one_fenced_json_block() -> None:
    lines = transcript(
        call("forecast_day"),
        event("tool_call_response", tool_call_id="1"),
        choice('```json\n{"hours": [10, 11]}\n```'),
    )
    assert proposal_from_transcript(lines) == {"hours": [10, 11]}


@pytest.mark.parametrize(
    ("lines", "reason"),
    [
        (transcript(choice(ANSWER)), "without reading the forecast"),
        (
            transcript(call("forecast_day"), event("tool_call_response"), choice("")),
            "no final answer",
        ),
        (
            transcript(
                call("forecast_day"),
                event("tool_call_response"),
                choice("The best hours are 10 and 11."),
            ),
            "Expecting value",
        ),
        # The run that motivated this gate: a correct-looking answer with no tool use.
        (transcript(call("__structured_output__", ANSWER)), "without reading the forecast"),
        (
            transcript(call("__structured_output__", ANSWER), call("forecast_day")),
            "without reading the forecast",
        ),
        (transcript(call("forecast_day")), "no final answer"),
        (b'{"type": "tool_call"\n', "Invalid transcript line 1"),
        (transcript(event("tool_call", tool_call={"function": {"name": 7}})), "Malformed"),
        (
            transcript(call("forecast_day"), call("__structured_output__", '{"a":1,"a":2}')),
            "Duplicate JSON key",
        ),
    ],
)
def test_rejects_missing_evidence_or_bad_transcripts(lines: bytes, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        proposal_from_transcript(lines)


def test_cli_prints_the_proposal_or_rejects(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["agent_evidence"])
    good = transcript(call("forecast_day"), call("__structured_output__", ANSWER))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(good)))
    main()
    assert json.loads(capsys.readouterr().out) == {"hours": [10, 11]}

    guess = transcript(call("__structured_output__", ANSWER))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(guess)))
    with pytest.raises(SystemExit) as raised:
        main()
    assert raised.value.code == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.startswith("Rejected: The agent answered without reading the forecast")
