"""
TfL Live Arrivals Fetcher (multi-station, multi-mode)
-------------------------------------------------------
Pulls live arrival predictions from the TfL Unified API for a chosen list
of station NAMES (not IDs) — automatically resolving each name to every
matching StopPoint across all transport modes (tube, bus, dlr, overground,
etc.), then stores each snapshot in a local SQLite database following a
star schema (fact_arrivals + dim_line, dim_station, dim_time).

Run this on a schedule (see README.md) to build up a history of live data
over time — that history is what your BI dashboard will visualize.

Setup:
    1. Get a free API key: https://api-portal.tfl.gov.uk/
    2. Put it in config.py (see config.py.example)
    3. pip install requests
    4. python fetch_tfl.py
"""

import sqlite3
import requests
import datetime
import json
from pathlib import Path

try:
    from config import APP_KEY, STATION_NAMES
    from config import MODE_FILTER
except ImportError:
    raise SystemExit(
        "Missing config.py. Copy config.py.example to config.py and add your "
        "TfL API key + station names before running this script."
    )

DB_PATH = Path(__file__).parent / "tfl_data.db"
STATION_CACHE_PATH = Path(__file__).parent / "station_id_cache.json"

SEARCH_URL = "https://api.tfl.gov.uk/StopPoint/Search/{query}"
ARRIVALS_URL = "https://api.tfl.gov.uk/StopPoint/{station_id}/Arrivals"
REQUEST_TIMEOUT = (5, 15)

PEAK_HOURS = set(range(7, 10)) | set(range(16, 19))  # 7-10am, 4-7pm


# ---------------------------------------------------------------------------
# Station name -> ID resolution (with local cache so we don't re-search
# every single run — only the first run per station name hits the search
# endpoint, after that it's read from station_id_cache.json)
# ---------------------------------------------------------------------------

def load_station_cache() -> dict:
    if STATION_CACHE_PATH.exists():
        with open(STATION_CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_station_cache(cache: dict):
    with open(STATION_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def resolve_station_ids(name: str) -> list:
    """Return a list of {id, name, modes} dicts matching this station name."""
    url = SEARCH_URL.format(query=requests.utils.quote(name))
    params = {"app_key": APP_KEY} if APP_KEY else {}
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    results = []
    seen_ids = set()
    for m in data.get("matches", []):
        stop_id = m.get("id")
        if not stop_id or stop_id in seen_ids:
            continue
        modes = m.get("modes", [])
        if MODE_FILTER and not any(mode in MODE_FILTER for mode in modes):
            continue
        seen_ids.add(stop_id)
        results.append({
            "id": stop_id,
            "name": m.get("name", stop_id),
            "modes": modes,
        })
    return results


def get_all_station_ids() -> list:
    """Resolve every name in STATION_NAMES to concrete StopPoint IDs,
    using and updating a local cache so repeated runs are fast and don't
    hammer the search endpoint."""
    cache = load_station_cache()
    all_ids = []
    cache_updated = False

    for name in STATION_NAMES:
        if name in cache:
            matches = cache[name]
        else:
            print(f"Looking up '{name}'...")
            matches = resolve_station_ids(name)
            cache[name] = matches
            cache_updated = True

        if not matches:
            print(f"  WARNING: no StopPoints found for '{name}' — skipping")
            continue

        for m in matches:
            all_ids.append(m["id"])

    if cache_updated:
        save_station_cache(cache)

    return list(dict.fromkeys(all_ids))  # de-duplicate, preserve order


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()


def get_or_create_time_id(conn, dt: datetime.datetime) -> int:
    date_str = dt.strftime("%Y-%m-%d")
    hour = dt.hour
    day_of_week = dt.strftime("%A")
    is_peak = 1 if (hour in PEAK_HOURS and dt.weekday() < 5) else 0

    cur = conn.execute(
        "SELECT time_id FROM dim_time WHERE date = ? AND hour = ?",
        (date_str, hour),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur = conn.execute(
        "INSERT INTO dim_time (date, hour, day_of_week, is_peak) VALUES (?, ?, ?, ?)",
        (date_str, hour, day_of_week, is_peak),
    )
    conn.commit()
    return cur.lastrowid


def upsert_dim_line(conn, line_id, line_name, mode):
    conn.execute(
        "INSERT OR IGNORE INTO dim_line (line_id, line_name, mode) VALUES (?, ?, ?)",
        (line_id, line_name, mode),
    )
    # mode can vary if TfL updates it — keep it fresh
    conn.execute(
        "UPDATE dim_line SET mode = ? WHERE line_id = ?",
        (mode, line_id),
    )


def upsert_dim_station(conn, station_id, station_name):
    conn.execute(
        "INSERT OR IGNORE INTO dim_station (station_id, station_name) VALUES (?, ?)",
        (station_id, station_name),
    )


# ---------------------------------------------------------------------------
# Fetch + store arrivals
# ---------------------------------------------------------------------------

def fetch_arrivals(station_id: str) -> list:
    url = ARRIVALS_URL.format(station_id=station_id)
    params = {"app_key": APP_KEY} if APP_KEY else {}
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def store_arrivals(conn, records: list):
    now = datetime.datetime.now()
    time_id = get_or_create_time_id(conn, now)
    pulled_at = now.isoformat(timespec="seconds")

    for rec in records:
        line_id = rec.get("lineId", "unknown")
        line_name = rec.get("lineName", line_id)
        mode = rec.get("modeName", "unknown")
        station_id = rec.get("naptanId", "unknown")
        station_name = rec.get("stationName", station_id)

        upsert_dim_line(conn, line_id, line_name, mode)
        upsert_dim_station(conn, station_id, station_name)

        conn.execute(
            """INSERT INTO fact_arrivals
               (line_id, station_id, time_id, destination_name,
                expected_arrival, time_to_station_sec, pulled_at, vehicle_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                line_id,
                station_id,
                time_id,
                rec.get("destinationName"),
                rec.get("expectedArrival"),
                rec.get("timeToStation"),
                pulled_at,
                rec.get("vehicleId"),
            ),
        )
    conn.commit()


def main():
    conn = get_connection()
    init_db(conn)

    station_ids = get_all_station_ids()
    print(f"Resolved {len(STATION_NAMES)} station names -> {len(station_ids)} StopPoints "
          f"(across all modes found)\n")

    if not station_ids:
        print("No stations resolved — check STATION_NAMES in config.py and your API key.")
        conn.close()
        return

    total_inserted = 0
    modes_seen = set()
    for station_id in station_ids:
        try:
            records = fetch_arrivals(station_id)
            store_arrivals(conn, records)
            total_inserted += len(records)
            for r in records:
                modes_seen.add(r.get("modeName", "unknown"))
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                  f"{station_id}: {len(records)} arrivals stored")
        except requests.RequestException as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                  f"ERROR fetching {station_id}: {e}")
            if isinstance(e, requests.HTTPError) and e.response is not None \
                  and e.response.status_code in (401, 403):
                print("TfL rejected APP_KEY. Create or activate a key at "
                    "https://api-portal.tfl.gov.uk/, update config.py, "
                    "and run again.")
                break

    print(f"\nDone. {total_inserted} total records inserted into {DB_PATH}")
    print(f"Modes captured this run: {', '.join(sorted(modes_seen)) if modes_seen else 'none'}")
    conn.close()


if __name__ == "__main__":
    main()