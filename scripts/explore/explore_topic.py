import json
import requests

URL = "https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/childhood_illness/topics/Scarlet-fever"

# Follow the first link at each level, printing what we find, until we reach data
for level in range(1, 7):
    r = requests.get(URL, timeout=30)
    print(f"--- Level {level}: {URL}")
    if not r.ok:
        print(f"ERROR {r.status_code}")
        break
    data = r.json()
    preview = json.dumps(data, indent=1)
    print(preview[:700] + ("\n   ... (truncated)" if len(preview) > 700 else ""))
    record = data[0] if isinstance(data, list) and data else data
    links = [v for v in record.values() if isinstance(v, str) and v.startswith("http")] if isinstance(record, dict) else []
    if not links:
        print("\nNo further links: this is the data level.")
        break
    URL = links[0]
