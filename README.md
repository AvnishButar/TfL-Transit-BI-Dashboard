# Live TfL Transit Dashboard — Data Pipeline

Builds a real, growing dataset of live London Underground/bus arrivals for a
BI portfolio project. This is Phase 1 (data pipeline). Phase 2 is connecting
Power BI or Tableau to the SQLite database and building the dashboard.

## What this does

1. Calls the TfL Unified API for a list of stations you choose
2. Stores each arrival prediction as a row in `fact_arrivals`
3. Automatically builds out `dim_line`, `dim_station`, and `dim_time`
4. Every time you run it, you add a new snapshot — run it every 5-15 minutes
   over a few days and you'll have a real time-series dataset to analyze

## Setup

```bash
cd tfl_dashboard
pip install -r requirements.txt --break-system-packages   # or use a venv
cp config.py.example config.py
```

1. Get a free API key: https://api-portal.tfl.gov.uk/ (instant, no approval wait)
2. Open `config.py` and paste your key into `APP_KEY`
3. Pick your stations. The 5 in `config.py.example` are placeholders — verify
   the real StopPoint IDs for stations you want using:
   `https://api.tfl.gov.uk/StopPoint/Search/{station name}`
   e.g. `https://api.tfl.gov.uk/StopPoint/Search/Oxford%20Circus`
   (this returns a JSON list — grab the `naptanId` for the entry you want)

## Run it once to test

```bash
python fetch_tfl.py
```

You should see output like:
```
[2026-08-24 ...] 940GZZLUOXC: 24 arrivals stored
Done. 120 total records inserted into tfl_data.db
```

If you get an error, check:
- Your API key is correct in `config.py`
- Your station IDs are valid (test the URL directly in a browser first)
- A `401` or `403` response means TfL rejected the key. Create or activate a
   key in the TfL API portal, replace `APP_KEY`, and run the script again. Do
   not publish the key; rotate it if it has been exposed.

## Schedule it to run automatically (this is what makes the data "live")

**On Mac/Linux (cron):**
```bash
crontab -e
# add this line to run every 10 minutes:
*/10 * * * * cd /full/path/to/tfl_dashboard && /usr/bin/python3 fetch_tfl.py >> log.txt 2>&1
```

**On Windows (Task Scheduler):**
Create a Basic Task → Trigger: Daily, repeat every 10 minutes → Action: start
`python.exe` with argument `fetch_tfl.py` and "Start in" set to this folder.

Let it run for at least 2-3 days before building your dashboard — you want
enough history to show trends (peak vs off-peak, weekday vs weekend, etc.)

## Connecting to Power BI

1. Power BI Desktop → Get Data → **Database → SQLite database** (you may need
   to install the SQLite ODBC driver first — search "SQLite ODBC driver
   Windows" if the connector doesn't appear)
2. Point it at `tfl_data.db`
3. Load all four tables (`fact_arrivals`, `dim_line`, `dim_station`, `dim_time`)
4. In Power BI's Model view, create relationships:
   - `fact_arrivals.line_id` → `dim_line.line_id`
   - `fact_arrivals.station_id` → `dim_station.station_id`
   - `fact_arrivals.time_id` → `dim_time.time_id`
5. Set the dashboard to refresh (Power BI Desktop refreshes on demand; for
   scheduled refresh you'd need Power BI Service + a gateway, which is
   optional — for a portfolio piece, manual refresh + screenshots over time
   is enough to show it's "live")

## Connecting to Tableau

Tableau Public/Desktop → Connect → **More → SQLite** (may need the SQLite
ODBC/JDBC driver depending on your OS) → same relationship setup as above.

## Suggested KPIs / visuals once you have data

- **Average time-to-station by line** — which lines run more/less predictably
- **Arrivals volume by hour** — peak vs off-peak patterns
- **Busiest stations** — count of arrivals tracked per station
- **Day-of-week patterns** — weekday vs weekend service levels
- A **time-series line chart** showing arrival volume over the days you
  collected data — this is your strongest "look, it's really live" visual

## Notes for your resume/portfolio writeup

Frame this project as: *"Built an end-to-end BI pipeline ingesting live
transit data via REST API into a dimensional (star schema) SQLite database,
with a Power BI dashboard tracking service reliability KPIs."* That one line
covers API integration, data modeling, and BI tooling — the three things a
BI Analyst JD usually asks for.
