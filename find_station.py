"""
Station ID Finder
------------------
Looks up TfL StopPoint (naptanId) values by station name, so you don't have
to guess or hardcode IDs. Use this to build your STATION_IDS list in config.py.

Usage:
    python find_station_id.py "Oxford Circus"
    python find_station_id.py "Bank" "Stratford" "Camden Town"
"""

import sys
import requests

try:
    from config import APP_KEY
except ImportError:
    APP_KEY = ""  # search endpoint works fine without a key too

SEARCH_URL = "https://api.tfl.gov.uk/StopPoint/Search/{query}"


def find_station(name: str):
    url = SEARCH_URL.format(query=requests.utils.quote(name))
    params = {"app_key": APP_KEY} if APP_KEY else {}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    matches = data.get("matches", [])
    if not matches:
        print(f"  No matches found for '{name}'")
        return

    print(f"\nResults for '{name}':")
    seen = set()
    for m in matches[:8]:
        naptan_id = m.get("id")
        common_name = m.get("name")
        modes = ", ".join(m.get("modes", []))
        key = (naptan_id, common_name)
        if key in seen:
            continue
        seen.add(key)
        print(f"  {naptan_id:20s}  {common_name:35s}  [{modes}]")


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_station_id.py \"Station Name\" [\"Another Station\" ...]")
        sys.exit(1)

    for name in sys.argv[1:]:
        find_station(name)


if __name__ == "__main__":
    main()