This sandbox plans electric vehicle charging from a synthetic solar forecast.

- The forecast is mounted read-only at `/forecast/day.json`. Only the workspace is writable.
  The planner ships inside the kit; the repository and the verifier are not in the sandbox.
- `solar-plan` prints a deterministic proposal as a JSON object with an `hours` array.
- Proposals are advisory. The host verifies each one against its own copy of the forecast and
  makes the final decision.
- The kit denies all runtime network egress. The task needs none.
