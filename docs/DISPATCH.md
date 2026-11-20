# Dispatch model

The forecast describes a set of eligible one-hour blocks. Each block delivers a fixed amount of charge to the vehicle. Blocks are independent and may be nonconsecutive. The goal is to deliver the requested charge using the smallest total amount of incremental grid energy.

## Forecast and calculation

The [example forecast](../lab/forecast/day.json) requests two one-hour blocks at 3 kW. Solar generation serves the household first. Any surplus can charge the vehicle during the same hour.

| Hour | Solar generation | Household use | Solar surplus | Grid energy for charging |
| --- | ---: | ---: | ---: | ---: |
| 09:00 | 1,600 Wh | 1,300 Wh | 300 Wh | 2,700 Wh |
| 10:00 | 3,900 Wh | 1,500 Wh | 2,400 Wh | 600 Wh |
| 11:00 | 4,800 Wh | 1,800 Wh | 3,000 Wh | 0 Wh |
| 12:00 | 3,600 Wh | 1,700 Wh | 1,900 Wh | 1,100 Wh |

The forecast uses integer watt-hours throughout.

```text
solar_surplus_wh = max(0, pv_wh - home_wh)
grid_wh = max(0, charge_wh - solar_surplus_wh)
```

The planner ranks blocks by grid energy, uses the earlier hour to break ties, and outputs the chosen hours in chronological order. The verifier accepts any optimal schedule in any order. It independently checks whether replacing a selected hour with an unused hour would reduce total grid energy.

## CLI contract

Both commands take the path to the forecast. The forecast provides `charge_wh`, `slots`, and an `hours` array of records with `hour`, `pv_wh`, and `home_wh`. It can contain at most 24 distinct hours, from 0 through 23.

- `plan` writes exactly one JSON object with an `hours` array to stdout.
- `verify` reads at most 4 KiB of proposal JSON from stdin. The object must contain only `hours`, with the requested number of distinct eligible hours.
- Both commands parse strict JSON. They reject duplicate keys at any depth, because parsers that keep the first or the last value would disagree about what the agent proposed. They also reject `NaN` and `Infinity`. On acceptance, it writes a JSON object with `decision`, `hours`, and `grid_wh`. On rejection, it prints a diagnostic to stderr and exits with status 1.

See the [development guide](DEVELOPMENT.md) for the accepted and rejected smoke tests.
