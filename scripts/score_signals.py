#!/usr/bin/env python3
"""
score_signals.py

How unusual is the latest value of every series? Saves data/scores.csv.

  Group A: z-score against the same time of year in previous years (2020-21 excluded)
  Group B: ratio to UKHSA's own published baseline
  Group C: ratio to the same period last year (lower confidence)
"""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
CLEAN = PROJECT / "data" / "clean"
TODAY = pd.Timestamp(date.today())

MAX_AGE_DAYS = {"daily": 30, "weekly": 70, "monthly": 120}  # older than this = not currently reported
WINDOW_DAYS = {"weekly": 14, "monthly": 35}                 # +/- around the same date in past years
EXCLUDE_YEARS = {2020, 2021}                                # pandemic years distort "normal"
LOOKBACK_YEARS = 8
MIN_PAST_YEARS = 3
Z_FLAG = 2.0
RATIO_FLAG = 1.5
SMALL_COUNT = 10


def to_weekly(df):
    """Daily data -> weekly averages (weeks starting Monday), for value and baseline."""
    df = df.copy()
    df["date"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    return df.groupby("date", as_index=False)[["value", "baseline"]].mean()


def seasonal_z(df, when, value, freq):
    """z-score of `value` against the same time of year in previous years."""
    win = pd.Timedelta(days=WINDOW_DAYS[freq])
    values, years = [], 0
    for k in range(1, LOOKBACK_YEARS + 1):
        centre = when - pd.Timedelta(days=round(365.25 * k))
        if centre.year in EXCLUDE_YEARS:
            continue
        near = df[(df["date"] >= centre - win) & (df["date"] <= centre + win)]["value"]
        if len(near):
            values.extend(near.tolist())
            years += 1
    if years < MIN_PAST_YEARS:
        return None, None, years
    mean = float(np.mean(values))
    spread = max(float(np.std(values)), 0.05 * abs(mean), 1e-9)  # guard against a near-zero spread
    return (value - mean) / spread, mean, years


def same_time_last_year(df, when, freq):
    win = pd.Timedelta(days=WINDOW_DAYS[freq])
    centre = when - pd.Timedelta(days=365)
    near = df[(df["date"] >= centre - win) & (df["date"] <= centre + win)]["value"]
    return float(near.mean()) if len(near) else None


def score(row, df):
    out = {"group": row["group"], "series_id": row["series_id"], "freq": row["freq"]}
    df = df[~df["in_delay"].astype(str).str.lower().eq("true")].copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["baseline"] = pd.to_numeric(df["baseline"], errors="coerce")
    df = df.dropna(subset=["value"]).sort_values("date")

    last = df["date"].max()
    age = (TODAY - last).days
    if age > MAX_AGE_DAYS[row["freq"]]:
        return {**out, "status": f"not currently reported (last data {last.date()})"}

    freq = row["freq"]
    if freq == "daily":
        df, freq = to_weekly(df), "weekly"
    latest = df.iloc[-1]
    out.update({"latest_date": latest["date"].date(), "latest_value": round(latest["value"], 3)})

    if row["group"] == "A":
        zs = []
        for _, p in df.tail(2).iterrows():
            z, expected, years = seasonal_z(df, p["date"], p["value"], freq)
            zs.append(z)
        if zs[-1] is None:
            return {**out, "status": f"only {years} usable past years"}
        out.update({"expected": round(expected, 3), "ratio": round(latest["value"] / expected, 2) if expected else None,
                    "z": round(zs[-1], 2), "past_years": years})
        both = all(z is not None and z >= Z_FLAG for z in zs)
        out["flag"] = "SIGNAL" if both else ("watch" if zs[-1] >= Z_FLAG else "")
        if zs[-1] <= -Z_FLAG:
            out["flag"] = "unusually low"

    elif row["group"] == "B":
        with_base = df.dropna(subset=["baseline"])
        with_base = with_base[with_base["baseline"] > 0]
        if with_base.empty:
            return {**out, "status": "no baseline available"}
        ratios = (with_base["value"] / with_base["baseline"]).tail(2).tolist()
        out.update({"expected": round(with_base.iloc[-1]["baseline"], 3), "ratio": round(ratios[-1], 2)})
        if with_base["date"].max() < df["date"].max():
            out["note"] = f"UKHSA baseline only published to {with_base['date'].max().date()}"
        both = len(ratios) == 2 and all(r >= RATIO_FLAG for r in ratios)
        out["flag"] = "SIGNAL" if both else ("watch" if ratios[-1] >= RATIO_FLAG else "")

    else:  # group C
        prev = same_time_last_year(df, latest["date"], freq)
        if not prev:
            return {**out, "status": "no data for the same time last year"}
        ratio = latest["value"] / prev
        out.update({"expected": round(prev, 3), "ratio": round(ratio, 2)})
        out["flag"] = "watch" if ratio >= RATIO_FLAG else ""
        if "count" in row["metric"].lower() and latest["value"] < SMALL_COUNT:
            out["note"] = "small numbers - treat with caution"

    out["status"] = "scored"
    return out


def main():
    series = pd.read_csv(CLEAN / "series.csv", parse_dates=["date"])
    cat = pd.read_csv(CLEAN / "series_catalogue.csv")

    results = [score(row, series[series["series_id"] == row["series_id"]]) for _, row in cat.iterrows()]
    scores = pd.DataFrame(results)
    scores.to_csv(PROJECT / "data" / "scores.csv", index=False)

    pd.set_option("display.width", 250, "display.max_rows", 200, "display.max_colwidth", 75)
    scored = scores[scores["status"] == "scored"]
    print(f"Scored {len(scored)} of {len(scores)} series (run date {TODAY.date()})\n")

    for group, sort_col, title in (("A", "z", "GROUP A - against the same time in past years (z-score)"),
                                   ("B", "ratio", "GROUP B - against UKHSA's own baseline (ratio)"),
                                   ("C", "ratio", "GROUP C - against the same time last year (ratio, low confidence)")):
        part = scored[scored["group"] == group].sort_values(sort_col, ascending=False)
        cols = [c for c in ("flag", "series_id", "latest_date", "latest_value", "expected", "ratio", "z",
                            "past_years", "note") if c in part.columns and part[c].notna().any()]
        print(f"=== {title} ===")
        print(part[cols].fillna("").to_string(index=False) if not part.empty else "  (none)")
        print()

    other = scores[scores["status"] != "scored"]
    if not other.empty:
        print("=== Not scored ===")
        print(other[["series_id", "status"]].to_string(index=False))


if __name__ == "__main__":
    main()
