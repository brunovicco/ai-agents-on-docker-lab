Choose two one-hour blocks to charge the vehicle. Read the synthetic forecast at
`/forecast/day.json` or through `forecast_day` if the task uses MCP. Each block delivers
`charge_wh` watt-hours. Use the solar surplus after household consumption to minimize
additional grid energy. Return a single JSON object with an `hours` array containing the
two selected hours. The exercise uses a simulated vehicle.
