#!/usr/bin/env python3
"""
clean_ukhsa.py

Turns the raw UKHSA files into tidy time series: one 'total' line per series.

Outputs:
  data/clean/series.csv            date-by-date values (series_id, date, value, baseline, in_delay)
  data/clean/series_catalogue.csv  one row per series: what it is, frequency, history, group (A/B/C)
  data/clean/cleaning_log.txt      every duplicate resolved, and how

Groups:
  A = long history (4+ years): we build our own seasonal baseline
  B = UKHSA publishes a baseline: compare against it
  C = short history, no baseline: year-on-year only, lower confidence
"""
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT / "data" / "raw"
CLEAN_DIR = PROJECT / "data" / "clean"
MIN_YEARS_FOR_OWN_BASELINE = 4
MAX_DUPLICATE_DATES = 5   # a few = data errors (resolve + log); more = our total rule is wrong (STOP)


def skip_reason(m):
    """Return why a measure is excluded, or None to keep it."""
    name = m["metric"]
    low = name.lower()
    if m["freq"] == "every 365d":
        return "yearly data: can't give early warning"
    if "averagerolling7day" in low:
        return "smoothed copy of another measure"
    if "baseline" in low:
        return "UKHSA baseline: attached to its measure, not a series itself"
    if name.endswith("countsByOnsetType"):
        return "snapshot table: the ByMonth version is used instead"
    if "numbertested" in low or "percenttested" in low:
        return "testing volume, not an infection signal"
    if name == "iGAS_cases_rateByMonth":
        return "split by age and sex with no total; rates can't be added"
    if "survey" in low:
        return "under 1 year of history"
    if name == "measles_cases_casesByOnsetWeek":
        return "replaced by the version excluding reporting lag"
    return None


def load_raw(m):
    df = pd.read_csv(RAW_DIR / f"{m['sub_theme']}__{m['topic']}__{m['metric']}.csv", parse_dates=["date"])
    for col in ("stratum", "sex", "age"):
        df[col] = df[col].astype(str)
    df["in_delay"] = df["in_reporting_delay_period"].astype(str).str.lower().eq("true")
    return df


def pick_series(df, metric):
    """Apply the 'which row is the total' rules. Returns a list of (part, frame)."""
    s, sx, ag = df["stratum"], df["sex"], df["age"]
    if (s == "Total cases").any():
        return [("total", df[s == "Total cases"])]
    if (s == "five_season_average").any():                       # norovirus
        return [("total", df[s == "count"])]
    if "PercentResistant" in metric:                              # one line per antibiotic
        return [(antibiotic, g) for antibiotic, g in df.groupby("stratum")]
    total = df[(s == "default") & (sx == "all") & (ag == "all")]
    if not total.empty:
        return [("total", total)]
    if metric == "mpox_cases_countByMonth":                       # counts: safe to add strains
        summed = df.groupby("date", as_index=False).agg(metric_value=("metric_value", "sum"),
                                                        in_delay=("in_delay", "any"))
        return [("total (sum of strains)", summed)]
    return []


def baseline_for(m, df):
    """Find UKHSA's baseline for this measure, if one is published. Returns date -> baseline."""
    if (df["stratum"] == "five_season_average").any():
        b = df[df["stratum"] == "five_season_average"]
        return b.groupby("date")["metric_value"].mean()
    for observed, expected in (("countsByDay", "baselineCountsByDay"), ("rateByDay", "baselineRateByDay")):
        if m["metric"].endswith(observed):
            path = RAW_DIR / f"{m['sub_theme']}__{m['topic']}__{m['metric'].replace(observed, expected)}.csv"
            if path.exists():
                b = pd.read_csv(path, parse_dates=["date"])
                b = b[(b["sex"].astype(str) == "all") & (b["age"].astype(str) == "all")]
                return b.groupby("date")["metric_value"].mean()
    return None


def resolve_duplicates(out, series_id, log, problems):
    """A few duplicate dates: keep one exact copy / average conflicting values, and log it.
    Many duplicate dates: our total rule is wrong for this measure, so report a problem."""
    dup = out[out["date"].duplicated(keep=False)]
    if dup.empty:
        return out
    n_dates = dup["date"].nunique()
    if n_dates > MAX_DUPLICATE_DATES:
        problems.append(f"{series_id}: {n_dates} dates with more than one value - check the total rule")
        return None
    for date, g in dup.groupby("date"):
        values = sorted(g["value"].unique())
        if len(values) == 1:
            log.append(f"{series_id} | {date.date()} | exact copy removed")
        else:
            log.append(f"{series_id} | {date.date()} | conflicting values {values} averaged to "
                       f"{sum(values) / len(values):.3f} (flagged uncertain)")
    return out.groupby("date", as_index=False).agg(value=("value", "mean"), in_delay=("in_delay", "any"))


def main():
    profile = pd.read_csv(PROJECT / "data" / "profile.csv")
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    all_series, catalogue, skipped, problems, log = [], [], [], [], []
    for _, m in profile.iterrows():
        reason = skip_reason(m)
        if reason:
            skipped.append(reason)
            continue
        df = load_raw(m)
        parts = pick_series(df, m["metric"])
        if not parts:
            problems.append(f"{m['metric']}: no rule for its groups")
            continue
        baseline = baseline_for(m, df)

        for part, frame in parts:
            series_id = f"{m['topic']} | {m['metric']}" + ("" if part == "total" else f" | {part}")
            out = frame[["date", "metric_value", "in_delay"]].rename(columns={"metric_value": "value"})
            out = out.dropna(subset=["value"]).sort_values("date")
            out = resolve_duplicates(out, series_id, log, problems)
            if out is None:
                continue
            out["baseline"] = out["date"].map(baseline) if baseline is not None else pd.NA
            out.insert(0, "series_id", series_id)
            all_series.append(out)

            years = round((out["date"].max() - out["date"].min()).days / 365.25, 1)
            has_baseline = baseline is not None and out["baseline"].notna().any()
            group = "B" if has_baseline else ("A" if years >= MIN_YEARS_FOR_OWN_BASELINE else "C")
            catalogue.append({"series_id": series_id, "sub_theme": m["sub_theme"], "topic": m["topic"],
                              "metric": m["metric"], "part": part, "freq": m["freq"],
                              "first": out["date"].min().date(), "last": out["date"].max().date(),
                              "years": years, "points": len(out), "group": group})

    if problems:
        print("STOP - problems found:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    series = pd.concat(all_series, ignore_index=True)
    cat = pd.DataFrame(catalogue).sort_values(["group", "sub_theme", "series_id"])
    series.to_csv(CLEAN_DIR / "series.csv", index=False)
    cat.to_csv(CLEAN_DIR / "series_catalogue.csv", index=False)
    (CLEAN_DIR / "cleaning_log.txt").write_text("\n".join(log) + "\n" if log else "No duplicates found\n")

    print(f"Measures skipped: {len(skipped)}")
    for reason, n in pd.Series(skipped).value_counts().items():
        print(f"   {n:>3}  {reason}")
    print(f"\nDuplicates resolved: {len(log)}")
    for line in log:
        print("   ", line)
    print(f"\nSeries created: {len(cat)}  ({len(series):,} data points)")
    print("By group:", cat["group"].value_counts().sort_index().to_dict(), "\n")
    pd.set_option("display.width", 220, "display.max_rows", 200, "display.max_colwidth", 80)
    print(cat[["group", "series_id", "freq", "first", "last", "years"]].to_string(index=False))


if __name__ == "__main__":
    main()
