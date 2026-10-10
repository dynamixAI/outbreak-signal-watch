#!/usr/bin/env python3
"""inspect_groups.py - show how split measures are divided, so we can pick the 'total' row."""
from collections import defaultdict
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT / "data" / "raw"
profile = pd.read_csv(PROJECT / "data" / "profile.csv")

split = profile[(profile["groups"] > 1) & (profile["freq"] != "every 365d")]

by_signature = defaultdict(list)
for _, m in split.iterrows():
    df = pd.read_csv(RAW_DIR / f"{m['sub_theme']}__{m['topic']}__{m['metric']}.csv")
    groups = sorted(set(df[["stratum", "sex", "age"]].astype(str).itertuples(index=False, name=None)))
    by_signature[tuple(groups)].append(f"{m['topic']}: {m['metric']}")

for i, (groups, measures) in enumerate(by_signature.items(), 1):
    print(f"\n=== Split type {i}: used by {len(measures)} measure(s) ===")
    print("Groups (stratum / sex / age):")
    for g in groups:
        print("   ", " / ".join(g))
    print("Measures:")
    for m in measures:
        print("   ", m)
