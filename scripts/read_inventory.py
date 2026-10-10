import csv
import re
from collections import Counter

FREQ = [("day", "daily"), ("week", "weekly"), ("month", "monthly"), ("quarter", "quarterly"), ("year", "yearly"), ("annual", "yearly")]
KIND = [("percent", "percent"), ("positivity", "percent"), ("rate", "rate"), ("count", "count"), ("total", "count"), ("cases", "count")]


def classify(name, rules):
    low = name.lower()
    for key, label in rules:
        if key in low:
            return label
    return "?"


rows = list(csv.DictReader(open("metrics_inventory.csv")))
for r in rows:
    r["freq"] = classify(r["metric"], FREQ)
    r["kind"] = classify(r["metric"], KIND)

print("How often measures are reported:", dict(Counter(r["freq"] for r in rows)))
print("What kind of number they are:  ", dict(Counter(r["kind"] for r in rows)), "\n")

current = None
for r in sorted(rows, key=lambda r: (r["sub_theme"], r["topic"])):
    label = f"{r['sub_theme']} / {r['topic']}"
    if label != current:
        print(f"\n{label}")
        current = label
    print(f"   [{r['freq']:>9} | {r['kind']:>7}]  {r['metric']}")
