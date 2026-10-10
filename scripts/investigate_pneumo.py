#!/usr/bin/env python3
"""Investigate S. pneumoniae resistance: yearly trend, recent months, and how many samples were tested."""
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PREFIX = "antimicrobial_resistance__S-pneumoniae__s-pneumoniae_testing_bacteraemia"


def load(kind):
    df = pd.read_csv(RAW / f"{PREFIX}{kind}RollingMonth.csv", parse_dates=["date"])
    return df.pivot_table(index="date", columns="stratum", values="metric_value")


resistant = load("PercentResistant")
tested = load("NumberTested")

print("=== Average % resistant by year (and average number tested per month) ===")
yearly = resistant.groupby(resistant.index.year).mean().round(2)
yearly_tested = tested.groupby(tested.index.year).mean().round(0)
print(yearly.join(yearly_tested, rsuffix=" (tested)").to_string())

print("\n=== Last 15 months ===")
recent = resistant.join(tested, rsuffix=" (tested)").tail(15)
print(recent.round(2).to_string())
