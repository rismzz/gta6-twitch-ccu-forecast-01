"""Forecast GTA VI's launch-day Twitch viewers hour by hour (program/v1).

Model: launch-day diurnal shape learned from the case's own comparables
(past big game launches, SullyGnome hourly Twitch category averages).

For each comparable with a complete release day (hours 1..24 present) whose
hour-1 count is at least 10% of its own day maximum -- which drops the
simultaneous-global launches whose hour 1 is still pre-unlock -- take the
log-ratio r_h = ln(v_h / v_1) for each hour h = 2..24.  Big launches are
already near their ceiling at hour 1 and grow little later, small launches
grow a lot (corr(log v_1, r_18) about -0.9 across the comparables), so per
hour we regress r_h on centred log v_1 with a slope shrunk by n / (n + 3),
then take the empirical quantiles of the residuals at the five scored
levels, widened 1.2x around their median and blended 25% toward a normal
with the residual spread (floor 0.15 in log units).  The forecast is

    q_tau(h) = p1 * exp(a_h + b_h * (ln p1 - m) + s_h(tau))

with p1 the case's hour-1 print, rounded half-up to 2 decimals.  The
log hour-1 entering the regression is capped at half a log unit past the
largest / smallest training launch, so a record-breaking hour 1 cannot
extrapolate the linear fit to absurd evening ratios.

Local validation (leave-one-out over the kit's comparables, scored with the
contest's log-scale pinball loss): pinball ~0.216, 90% coverage ~0.89,
typical median miss ~40%, against the house baseline's ~0.26-0.39 on the
same curves.  Deterministic, standard library only, no network, runs in
well under a second per case.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.6448536269514722, -0.6744897501960817, 0.0,
     0.6744897501960817, 1.6448536269514722]

# A comparable counts as a rolling-midnight launch (hour 1 already live)
# when its hour-1 print is at least this share of its own day maximum.
MIN_H1_SHARE = 0.10
MIN_CURVES = 8
# Regression shrinkage, tail widening and normal blend (tuned by LOO).
SHRINK_K = 3.0
TAIL_WIDEN = 1.2
NORMAL_BLEND = 0.25
SIGMA_FLOOR = 0.15
BASELINE_SIGMA = 0.15
# The log hour-1 adjustment is a linear fit: never extrapolate it more
# than this far (in log units) past the largest / smallest training
# launch, so a record-breaking hour 1 (GTA VI may dwarf every comparable)
# cannot drive the evening ratios to absurd values.
EXTRAPOLATION_CAP = 0.5


def round2(x):
    """Round half up to 2 decimals, as JavaScript Math.round(x*100)/100."""
    scaled = x * 100.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100.0
    return int(value) if float(value).is_integer() else value


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def quantile(xs, p):
    """Linear-interpolation quantile of a sorted-or-not list."""
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    if n == 1:
        return s[0]
    idx = p * (n - 1)
    lo = int(idx)
    frac = idx - lo
    return s[lo] * (1.0 - frac) + s[min(lo + 1, n - 1)] * frac


def parse_time(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def release_day_curve(comp):
    """Hour 1..24 viewers of a comparable's release day, or None.

    Returns None unless every hour is present with a positive count.
    The target's own pre-release history entry has no real release day
    and is dropped here by the completeness requirement.
    """
    day_start = parse_time(comp.get("day_start"))
    if day_start is None:
        return None
    hours = {}
    for row in comp.get("hourly") or []:
        viewers = row.get("viewers")
        if viewers is None or viewers <= 0:
            continue
        at = parse_time(row.get("from"))
        if at is None:
            continue
        delta = (at - day_start).total_seconds() / 3600.0
        if 0 <= delta < 24 and delta == int(delta):
            hours[int(delta) + 1] = float(viewers)
    if len(hours) != 24 or hours.get(1) is None:
        return None
    return hours


def select_curves(comparables):
    """Complete release-day curves, dropping pre-unlock hour-1 launches.

    Relaxes the hour-1 share threshold if too few curves survive.
    """
    curves = []
    for comp in comparables or []:
        hours = release_day_curve(comp)
        if hours is not None:
            curves.append(hours)
    for share in (MIN_H1_SHARE, 0.05, 0.0):
        kept = [h for h in curves if h[1] >= share * max(h.values())]
        if len(kept) >= MIN_CURVES or share == 0.0:
            return kept
    return curves


def fit_shape(curves):
    """Per-hour (centre, slope, mean-log-h1, residual quantiles).

    centre/slope describe the median log-ratio as a shrunk linear function
    of log hour-1; residual quantiles are the five scored levels of the
    regression residuals, widened and blended toward a normal.
    """
    n = len(curves)
    log_h1 = [math.log(h[1]) for h in curves]
    mean_log_h1 = sum(log_h1) / n
    # Bounds for the log hour-1 used in the adjustment (see the cap).
    log_h1_lo = min(log_h1) - EXTRAPOLATION_CAP
    log_h1_hi = max(log_h1) + EXTRAPOLATION_CAP
    shape = {}
    for hour in range(2, 25):
        ratios = [math.log(h[hour] / h[1]) for h in curves]
        mean_ratio = sum(ratios) / n
        num = sum((x - mean_log_h1) * (y - mean_ratio)
                  for x, y in zip(log_h1, ratios))
        den = sum((x - mean_log_h1) ** 2 for x in log_h1)
        slope = (num / den) if den else 0.0
        slope *= n / (n + SHRINK_K)
        residuals = [y - (mean_ratio + slope * (x - mean_log_h1))
                     for x, y in zip(log_h1, ratios)]
        med = median(residuals)
        var = sum((r - med) ** 2 for r in residuals) / n
        sigma = max(SIGMA_FLOOR, math.sqrt(var))
        emp = [quantile(residuals, tau) for tau in LEVELS]
        widened = [med + (q - med) * TAIL_WIDEN for q in emp]
        normal = [med + z * sigma for z in Z]
        blended = [(1.0 - NORMAL_BLEND) * w + NORMAL_BLEND * nn
                   for w, nn in zip(widened, normal)]
        shape[hour] = (mean_ratio, slope, mean_log_h1, blended)
    return shape, log_h1_lo, log_h1_hi


def baseline_quantiles(p1, hour):
    """House persistence baseline (used only if no curve survives)."""
    spread = BASELINE_SIGMA * math.sqrt(hour - 1)
    return [p1 * math.exp(z * spread) for z in Z]


def forecast_case(case):
    if case.get("levels") != LEVELS:
        raise ValueError("levels are not %r" % (LEVELS,))
    first = next((k for k in case.get("known") or [] if k.get("hour") == 1),
                 None)
    if first is not None and first.get("viewers"):
        p1 = max(1.0, float(first["viewers"]))
    else:
        history = case.get("history") or []
        p1 = 1.0
        for point in history:
            if point.get("viewers"):
                p1 = max(1.0, float(point["viewers"]))
    curves = select_curves(case.get("comparables"))
    shape = None
    log_h1_lo = log_h1_hi = None
    if curves:
        shape, log_h1_lo, log_h1_hi = fit_shape(curves)
    log_p1 = math.log(p1)
    if shape is not None:
        # Cap the extrapolation: a record hour 1 adjusts the shape as if
        # it were at most half a log unit past the biggest training launch.
        log_p1 = min(log_h1_hi, max(log_h1_lo, log_p1))
    rows = []
    for row in case.get("forecast") or []:
        hour = int(row["hour"])
        if shape is not None:
            centre, slope, mean_log_h1, resid_q = shape[hour]
            adj = centre + slope * (log_p1 - mean_log_h1)
            qs = [p1 * math.exp(adj + q) for q in resid_q]
        else:
            qs = baseline_quantiles(p1, hour)
        clean = []
        prev = 0.0
        for q in qs:
            value = round2(min(1e9, max(q, 1e-9)))
            if value < 1e-9:
                value = 0.01
            if value < prev:
                value = prev
            clean.append(value)
            prev = value
        rows.append({"hour": hour, "q": clean})
    rows.sort(key=lambda r: r["hour"])
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case)
        out = OUTPUT_DIR / (path.stem + ".out")
        out.write_text(json.dumps(forecast, separators=(",", ":")) + "\n",
                       encoding="utf-8")


if __name__ == "__main__":
    main()
