#!/usr/bin/env python3
"""profile_raw.py - summarise every raw UKHSA file before cleaning. Saves data/profile.csv."""
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT / "data" / "raw"


def frequency(dates):
    """Guess how often data is reported from the typical gap between dates."""
    gaps = dates.drop_duplicates().sort_values().diff().dt.days.dropna()
    if gaps.empty:
        return "single"
    days = gaps.median()
    if days <= 1:
        return "daily"
    if days <= 8:
        return "weekly"
    if days <= 31:
        return "monthly"
    return f"every {int(days)}d"


rows = []
for path in sorted(RAW_DIR.glob("*.csv")):
    sub_theme, topic, metric = path.stem.split("__")
    df = pd.read_csv(path, parse_dates=["date"])
    groups = df[["stratum", "sex", "age"]].drop_duplicates()
    rows.append({
        "sub_theme": sub_theme,
        "topic": topic,
        "metric": metric,
        "freq": frequency(df["date"]),
        "first": df["date"].min().date(),
        "last": df["date"].max().date(),
        "years": round((df["date"].max() - df["date"].min()).days / 365.25, 1),
        "rows": len(df),
        "rows_per_date": round(len(df) / df["date"].nunique(), 1),
        "groups": len(groups),
        "group_examples": "; ".join(f"{s}/{x}/{a}" for s, x, a in groups.head(4).itertuples(index=False)),
        "delay_rows": int(df["in_reporting_delay_period"].astype(str).str.lower().eq("true").sum()),
    })

profile = pd.DataFrame(rows)
profile.to_csv(PROJECT / "data" / "profile.csv", index=False)

print("How often:", profile["freq"].value_counts().to_dict())
print("Measures split into groups (more than 1 row per date):", int((profile["rows_per_date"] > 1).sum()))
print("Measures with under 3 years of history:", int((profile["years"] < 3).sum()), "\n")

pd.set_option("display.width", 250, "display.max_rows", 200, "display.max_colwidth", 45)
print(profile[["topic", "metric", "freq", "first", "last", "years", "rows_per_date", "groups", "delay_rows"]]
      .to_string(index=False))
print("\nSaved data/profile.csv")
