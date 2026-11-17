# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/rismzz/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/rismzz/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecast how many people watch Grand Theft Auto VI live on Twitch in each
hour of its release day (2026-11-19 UTC), after the first: for hours 2–24,
five quantiles (5%, 25%, 50%, 75%, 95%) of that hour's concurrent viewers,
scored by pinball loss on the log scale. One file, `main.py` (Python 3.13,
standard library only, no network, deterministic).

## The model

Launch-day diurnal shape learned at run time from the case's own
comparables — past big game launches' hourly Twitch category averages:

1. **Select rolling-midnight launches.** A comparable counts only if its
   release day is complete (hours 1–24 present) and its hour-1 count is at
   least 10% of its own day maximum. That drops the simultaneous-global
   launches (Silksong, Battlefield 6, …) whose hour 1 is still pre-unlock
   and whose ratios would be meaningless for a rolling launch like GTA VI.
2. **Anchor on hour 1, adjusted for launch size.** Big launches are already
   near their ceiling at hour 1 and grow little later; small launches grow
   a lot (corr(log hour-1, log-ratio at hour 18) ≈ −0.9 across the
   comparables). So per hour we regress the log-ratio
   ln(v_h / v_1) on centred log v_1, with the slope shrunk by n/(n+3).
3. **Honest spreads.** The five quantiles are the empirical quantiles of
   the regression residuals, widened 1.2× around their median and blended
   25% toward a normal with the residual spread (floor 0.15 log units).
4. **No runaway extrapolation.** The log hour-1 entering the regression is
   capped at half a log unit past the largest/smallest training launch, so
   a record-breaking hour 1 (GTA VI may dwarf every comparable) cannot
   drive the evening ratios to absurd values.

Typical shape it produces: the median dips below hour 1 in the small hours
(before the US unlocks at 05:00/08:00 UTC), then rises to roughly 1.5–2×
hour 1 in the US evening (hours 18–20) and eases off toward hour 24.

## Validation (leave-one-out over the kit's comparables)

Each comparable's release day is held out in turn, the model is fitted on
the rest, and the forecast is scored against the held-out day with the
contest's log-scale pinball loss:

| model | pinball loss | 90% coverage | typical median miss |
|---|---|---|---|
| this entry | **0.218** | 0.89 | ~41% |
| house baseline (persistence) | 0.297 | 0.84 | ~51% |

The house baseline scores ~0.387 on the official practice cases; this
model's shape advantage over persistence should carry over, since the
practice launches are rolling-midnight launches of the same kind.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` case in the input directory and writes one `*.out` per
case: `{"hours": [{"hour": 2, "q": [q05, q25, q50, q75, q95]}, …]}`,
23 rows, hours 2–24. Two runs on the same case produce byte-identical
output; a run of all four practice cases takes ~0.2 s.
