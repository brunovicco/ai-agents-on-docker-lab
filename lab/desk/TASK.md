# Task: propose a charging schedule

1. Call the `forecast_day` MCP tool to read the synthetic forecast.
2. Each listed hour can charge the simulated vehicle with `charge_wh` watt-hours. Choose `slots`
   distinct hours. For each hour, the solar surplus is `max(0, pv_wh - home_wh)` and the grid
   energy is `max(0, charge_wh - surplus)`. Minimize the total grid energy.
3. Write only the JSON object `{"hours": [...]}` to `/tmp/solar-answer.json`.

The host verifies the file against its own copy of the forecast. It rejects extra fields, repeated
keys, duplicate hours, and any schedule that has a cheaper alternative.
