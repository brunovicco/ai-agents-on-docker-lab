import json
from pathlib import Path

import pytest

from solar_dispatch.domain.dispatch import Forecast


def test_dispatch_contract() -> None:
    day = json.loads(Path("lab/forecast/day.json").read_text())
    forecast = Forecast.parse(day)
    assert forecast.propose() == [10, 11]
    assert forecast.verify([11, 10]) == 600
    for invalid in [[9, 12], [11, 11], [10, True], [10], [10, 25], {}]:
        with pytest.raises(ValueError):
            forecast.verify(invalid)
    for bad_day in [
        None,
        {},
        {**day, "slots": 0},
        {**day, "hours": [None] * 3},
        {**day, "hours": day["hours"] * 2},
        {**day, "hours": [{"hour": 0, "pv_wh": -1, "home_wh": 7}], "slots": 1},
    ]:
        with pytest.raises(ValueError):
            Forecast.parse(bad_day)


def test_cli_reads_proposal_on_operator_side(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io
    import sys

    from solar_dispatch.entrypoints.dispatch import main

    path = "lab/forecast/day.json"
    monkeypatch.setattr(sys, "argv", ["dispatch", "plan", path])
    main()
    plan = capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["dispatch", "verify", path])
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(plan.encode())))
    main()
    assert json.loads(capsys.readouterr().out)["grid_wh"] == 600
    rejected_proposals = [
        (b"x", "Expecting value"),
        (b" " * 4097, "Proposal exceeds 4 KiB"),
        (b'{"hours":[9,12]}', "A schedule with lower grid energy is available"),
        (b'{"hours":[10,11],"grid_wh":0}', "Invalid proposal format"),
        # A last-key-wins parser would accept the optimal second value.
        (b'{"hours":[9,12],"hours":[10,11]}', "Duplicate JSON key"),
        (b'{"hours":[10,NaN]}', "Non-standard JSON constant NaN"),
    ]
    for payload, reason in rejected_proposals:
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload)))
        with pytest.raises(SystemExit) as raised:
            main()
        assert raised.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert output.err.startswith(f"Rejected: {reason}")


def test_strict_json_rejects_nested_duplicates_and_infinity() -> None:
    from solar_dispatch.entrypoints.dispatch import load_strict_json

    assert load_strict_json('{"a": {"b": 1}}') == {"a": {"b": 1}}
    for text in ['{"a": {"b": 1, "b": 2}}', '{"a": Infinity}', '{"a": -Infinity}']:
        with pytest.raises(ValueError):
            load_strict_json(text)


def test_cli_rejects_forecast_with_duplicate_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import sys

    from solar_dispatch.entrypoints.dispatch import main

    day = Path("lab/forecast/day.json").read_text()
    forecast = tmp_path / "day.json"
    forecast.write_text(day.replace('"slots":2', '"slots":2,"slots":1'))
    monkeypatch.setattr(sys, "argv", ["dispatch", "plan", str(forecast)])
    with pytest.raises(SystemExit) as raised:
        main()
    assert raised.value.code == 1
    assert capsys.readouterr().err.startswith("Rejected: Duplicate JSON key")
