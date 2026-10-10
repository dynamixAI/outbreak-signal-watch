#!/usr/bin/env python3
"""audit_duplicates.py - check every raw file for more than one row per date and group."""
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT / "data" / "raw"
KEY = ["date", "stratum", "sex", "age"]

results = []
for path in sorted(RAW_DIR.glob("*.csv")):
    df = pd.read_csv(path, dtype=str)
    dup = df[df.duplicated(KEY, keep=False)]
    if dup.empty:
        continue
    per_key = dup.groupby(KEY)["metric_value"].nunique()
    differing = [c for c in df.columns if c not in KEY and dup.groupby(KEY)[c].nunique().max() > 1]
    results.append({
        "file": path.stem.split("__", 2)[2],
        "rows": len(df),
        "dup_keys": len(per_key),
        "exact_copies": int((per_key == 1).sum()),
        "conflicting": int((per_key > 1).sum()),
        "from": dup["date"].min(),
        "to": dup["date"].max(),
        "columns_that_differ": ", ".join(differing) or "none",
    })

files = len(list(RAW_DIR.glob("*.csv")))
print(f"Checked {files} files. Files with duplicates: {len(results)}\n")
if results:
    pd.set_option("display.width", 250, "display.max_colwidth", 70)
    print(pd.DataFrame(results).to_string(index=False))
