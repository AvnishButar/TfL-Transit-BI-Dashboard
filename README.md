# TfL-Transit-BI-Dashboard


An end-to-end Business Intelligence project that ingests **live data from the Transport for London (TfL) API**, models it into a star schema, and visualizes service reliability in an interactive Power BI dashboard.

![Dashboard Overview](screenshots/overview.png)
<!-- Replace with your actual screenshot filenames once added to a /screenshots folder -->

**[Live Dashboard →](https://noidainstituteofengtech-my.sharepoint.com/:u:/g/personal/0221csds219_niet_co_in/IQBICNlK61-ORod-zz1b7ML3ARKhcShP-IdblKfvVsry0Ts?e=aGko1x)** <!-- Add your Power BI "Publish to Web" link here once published -->

---

## What this project does

Most portfolio dashboards use a static Kaggle CSV. This one doesn't — it pulls **live, constantly-changing arrival data** for buses, the Underground, river-boats, and DLR across London, storing a fresh snapshot every few minutes to build a real time-series dataset. The result is a dashboard that reflects actual operational patterns: which lines run less predictably, how wait times shift through the day, and which stops see the most service.

## Tech stack

- **Python** — API integration, ETL, scheduled data collection
- **SQLite** — star-schema data warehouse
- **TfL Unified API** — live arrivals data source
- **Power BI** — data modeling (DAX), dashboard design
- **Windows Task Scheduler** — automated recurring data collection

## Data model

The database follows a standard star schema:

```
fact_arrivals
├── line_id      → dim_line (line_name, mode)
├── station_id   → dim_station (station_name)
└── time_id      → dim_time (date, hour, day_of_week, is_peak)
```

`fact_arrivals` stores one row per live arrival prediction, including the time-to-arrival in seconds (`time_to_station_sec`) and when it was captured (`pulled_at`).

## How it works

1. **`fetch_tfl.py`** resolves a list of station names to TfL StopPoint IDs (across all transport modes: tube, bus, DLR, river-bus, overground), then calls the live Arrivals API for each and inserts the results into `tfl_data.db`.
2. **Windows Task Scheduler** runs this script automatically every 10–15 minutes, so the dataset keeps growing on its own without manual intervention.
3. **`export_to_csv.py`** exports the four star-schema tables to CSV for a clean, driver-free Power BI import.
4. **Power BI** models the relationships, calculates DAX measures (avg wait time, peak vs off-peak, arrivals volume), and renders the dashboard.

## Dashboard pages

**Overview** — KPI cards (total arrivals tracked, average wait time), a live trend line of wait time by hour, and a mode/station slicer for interactivity.

**Deep Dive** — Worst-performing stops by average wait time, peak vs off-peak comparison, a per-line performance table, and a breakdown of data volume by transport mode.

## Key insight

<!-- Fill in your own real numbers here from the finished dashboard -->
Across the tracked stops, average wait time is noticeably higher during the evening peak window (4–7pm) than off-peak, and river-bus/bus stops account for the majority of captured volume in this run, with average wait times trending higher at riverside piers than at central Underground stations.

## Setup

```bash
git clone <this-repo>
cd tfl-dashboard
pip install -r requirements.txt --break-system-packages

cp config.py.example config.py
# add your free TfL API key (https://api-portal.tfl.gov.uk/) to config.py
# and customize STATION_NAMES to the stops you want to track

python fetch_tfl.py          # test a single run
python export_to_csv.py      # export tables for Power BI
```

Then schedule `fetch_tfl.py` to run every 10–15 minutes (Task Scheduler on Windows, cron on Mac/Linux) and let it collect for a few days before analyzing — the more snapshots collected, the more meaningful the time-based patterns become.

Open `TFL.pbix` in Power BI Desktop, or load the CSVs from `/exports` via **Get Data → Text/CSV**, and set up the relationships described in the data model above.

## Known limitations

- **"Wait time," not "delay":** TfL's live feed reports predicted time-to-arrival, not a comparison against a published schedule — so this measures service frequency/wait time rather than true delay against a timetable.
- **Mode coverage depends on station name matches:** searching by station name can pull in nearby stops across multiple modes (e.g. river-bus piers sharing a name with a nearby Underground station), which can skew mode-level comparisons. Worth filtering `MODE_FILTER` in `config.py` if you want a single-mode analysis.

## What this demonstrates

- REST API integration and ETL pipeline design
- Dimensional (star schema) data modeling
- DAX measures and time-intelligence calculations
- Automated, scheduled data collection (not a one-off static dataset)
- BI dashboard design: KPIs, drill-downs, and interactive filtering
