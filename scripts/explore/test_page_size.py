import requests

URL = ("https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/"
       "invasive_bacterial_infections/topics/iGAS/geography_types/Nation/"
       "geographies/England/metrics/iGAS_cases_countByWeek")

for size in (100, 365, 1000):
    r = requests.get(URL, params={"page_size": size}, timeout=30)
    if not r.ok:
        print(f"page_size={size}: ERROR {r.status_code}")
        continue
    data = r.json()
    print(f"page_size={size}: got {len(data['results'])} rows, total {data['count']}, more pages: {data['next'] is not None}")
