This sandbox plans electric vehicle charging from a synthetic solar forecast.

- The forecast is mounted read-only at `/forecast/day.json`. The planner source is mounted
  read-only at `/lab-src`. Only the workspace is writable.
- `solar-plan` prints a deterministic proposal as a JSON object with an `hours` array.
- Proposals are advisory. The host verifies each one against its own copy of the forecast and
  makes the final decision.
- The task needs no network access.
