-- TfL Live Transit Dashboard — Star Schema
-- Run this once to create the database structure.

CREATE TABLE IF NOT EXISTS dim_line (
    line_id     TEXT PRIMARY KEY,   -- e.g. "victoria", "central"
    line_name   TEXT NOT NULL,      -- e.g. "Victoria"
    mode        TEXT NOT NULL       -- e.g. "tube", "bus", "overground"
);

CREATE TABLE IF NOT EXISTS dim_station (
    station_id      TEXT PRIMARY KEY,  -- TfL naptan/stop id
    station_name    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,      -- YYYY-MM-DD
    hour            INTEGER NOT NULL,   -- 0-23
    day_of_week     TEXT NOT NULL,      -- Monday, Tuesday, ...
    is_peak         INTEGER NOT NULL,   -- 1 = peak (7-10am, 4-7pm weekdays), 0 = off-peak
    UNIQUE(date, hour)
);

CREATE TABLE IF NOT EXISTS fact_arrivals (
    arrival_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id             TEXT NOT NULL,
    station_id          TEXT NOT NULL,
    time_id             INTEGER NOT NULL,
    destination_name    TEXT,
    expected_arrival     TEXT NOT NULL,   -- raw ISO timestamp from API
    time_to_station_sec INTEGER,          -- seconds until arrival, as reported by API
    pulled_at            TEXT NOT NULL,   -- when this script fetched the record
    vehicle_id           TEXT,            -- unique per bus/train, helps de-dupe
    FOREIGN KEY (line_id) REFERENCES dim_line(line_id),
    FOREIGN KEY (station_id) REFERENCES dim_station(station_id),
    FOREIGN KEY (time_id) REFERENCES dim_time(time_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_line ON fact_arrivals(line_id);
CREATE INDEX IF NOT EXISTS idx_fact_station ON fact_arrivals(station_id);
CREATE INDEX IF NOT EXISTS idx_fact_time ON fact_arrivals(time_id);
