#!/usr/bin/env python3
"""
download_ukhsa.py

Downloads the full history of every daily, weekly and monthly England-level metric
in the UKHSA data dashboard API (except COVID-19 and yearly measures) into data/raw/.

Uses metrics_inventory.csv (built by build_inventory.py) as the list of metrics.
Usage:  python3 scripts/download_ukhsa.py            (skips files already downloaded)
        python3 scripts/download_ukhsa.py --refresh  (downloads everything again)
"""

import csv
import sys
import time
from pathlib import Path

import requests

# ---------- Settings ----------
PROJECT = Path(__file__).resolve().parent.parent
INVENTORY = PROJECT / "metrics_inventory.csv"
RAW_DIR = PROJECT / "data" / "raw"
PAGE_SIZE = 365                      # the API's maximum (tested)
SKIP_TOPICS = {"COVID-19"}           # already heavily covered, not "overlooked"
SKIP_IF_NAME_CONTAINS = ("byyear",)  # yearly figures can't give early warnings
REFRESH = "--refresh" in sys.argv


def get_page(url, retries=3):
    """Fetch one page, retrying a few times if the connection fails."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params={"page_size": PAGE_SIZE}, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as err:
            if attempt == retries:
                raise
            print(f"      retry {attempt} after error: {err}")
            time.sleep(2 * attempt)


def fetch_all(url):
    """Follow 'next' links until every page is collected. Returns (rows, expected_count, pages)."""
    rows, pages = [], 0
    first = get_page(url)
    expected = first.get("count", 0)
    data = first
    while True:
        rows.extend(data.get("results", []))
        pages += 1
        if not data.get("next"):
            break
        time.sleep(0.2)                       # be polite to the server
        data = get_page(data["next"])
    return rows, expected, pages


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    metrics = list(csv.DictReader(open(INVENTORY)))

    wanted = [m for m in metrics
              if m["topic"] not in SKIP_TOPICS
              and not any(word in m["metric"].lower() for word in SKIP_IF_NAME_CONTAINS)]
    print(f"{len(wanted)} of {len(metrics)} metrics selected\n")

    done = skipped = empty = 0
    problems = []
    for m in wanted:
        filename = f"{m['sub_theme']}__{m['topic']}__{m['metric']}.csv"
        target = RAW_DIR / filename
        if target.exists() and not REFRESH:
            skipped += 1
            continue
        try:
            rows, expected, pages = fetch_all(m["link"])
        except requests.RequestException as err:
            problems.append(f"FAILED {m['metric']}: {err}")
            print(f"  FAILED  {m['metric']}")
            continue
        if not rows:
            empty += 1
            print(f"  EMPTY   {m['metric']}")
            continue

        with open(target, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        dates = sorted(r["date"] for r in rows if r.get("date"))
        status = "OK" if len(rows) == expected else f"MISMATCH (expected {expected})"
        if status != "OK":
            problems.append(f"{m['metric']}: got {len(rows)} rows, expected {expected}")
        print(f"  {status:<8} {m['topic']:<32} {len(rows):>6} rows  {dates[0]} to {dates[-1]}  ({pages} pages)  {m['metric']}")
        done += 1

    print(f"\nDone: {done} downloaded, {skipped} already had, {empty} empty, {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)


if __name__ == "__main__":
    main()
