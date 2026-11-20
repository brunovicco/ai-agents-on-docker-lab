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
    ]
    for payload, reason in rejected_proposals:
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload)))
        with pytest.raises(SystemExit) as raised:
            main()
        assert raised.value.code == 1
        output = capsys.readouterr()
        assert output.out == ""
        assert output.err.startswith(f"Rejected: {reason}")
