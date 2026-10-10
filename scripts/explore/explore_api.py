import requests

BASE = "https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/"


def get_json(url):
    """Fetch a URL and return its JSON, or None if it fails."""
    r = requests.get(url.split("?")[0], timeout=30)
    if not r.ok:
        print(f"   ERROR {r.status_code} at {url}")
        return None
    return r.json()


def first_item(data):
    """The API sometimes wraps a single record in a list: [ {...} ]. Unwrap it."""
    if isinstance(data, list):
        return data[0] if data else {}
    return data or {}


subs = get_json(BASE)
example_shown = False

for s in subs:
    level2 = first_item(get_json(s["link"]))     # now a dict: {'topics': <link>}
    if "topics" not in level2:
        print(f"{s['name']}: no topics link (got {type(level2).__name__}: {level2})")
        continue
    topics = get_json(level2["topics"])          # the list of diseases
    if not topics:
        continue
    if not example_shown:
        print("Example topic item:", topics[0], "\n")
        example_shown = True
    names = [t.get("name", str(t)) if isinstance(t, dict) else str(t) for t in topics]
    print(f"{s['name']} ({len(names)}): {', '.join(names)}")
