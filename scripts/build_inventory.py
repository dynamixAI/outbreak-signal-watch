import csv
import time
import requests

BASE = "https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/"


def get_json(url):
    r = requests.get(url.split("?")[0], timeout=30)
    return r.json() if r.ok else None


def first_item(data):
    if isinstance(data, list):
        return data[0] if data else {}
    return data or {}


rows = []
for s in get_json(BASE):
    topics_link = first_item(get_json(s["link"])).get("topics")
    for t in get_json(topics_link) or []:
        metrics_url = f"{t['link']}/geography_types/Nation/geographies/England/metrics"
        metrics = get_json(metrics_url) or []
        names = [m["name"] for m in metrics]
        print(f"{s['name']} / {t['name']}: {len(names)} metric(s)")
        for name in names:
            rows.append({"sub_theme": s["name"], "topic": t["name"], "metric": name,
                         "link": f"{metrics_url}/{name}"})
        time.sleep(0.3)   # be polite to the API

with open("metrics_inventory.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["sub_theme", "topic", "metric", "link"])
    writer.writeheader()
    writer.writerows(rows)

print(f"\nSaved {len(rows)} metrics to metrics_inventory.csv")
