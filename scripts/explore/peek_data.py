import json
import requests

URL = ("https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/"
       "invasive_bacterial_infections/topics/iGAS/geography_types/Nation/"
       "geographies/England/metrics/iGAS_cases_countByWeek")

r = requests.get(URL, timeout=30)
print("Status:", r.status_code)
data = r.json()

print("Top-level keys:", list(data) if isinstance(data, dict) else f"a list of {len(data)} items")
if isinstance(data, dict):
    for key in ("count", "next", "previous"):
        print(f"  {key}: {data.get(key)}")
    rows = data.get("results", [])
else:
    rows = data

print(f"\nRows on this page: {len(rows)}")
print("\nFirst row:\n", json.dumps(rows[0], indent=1) if rows else "none")
print("\nLast row:\n", json.dumps(rows[-1], indent=1) if rows else "none")
