"""Load the TfL SQLite tables into Power BI through Python."""

import sqlite3
from pathlib import Path

import pandas as pd
import matplotlib as plt

DB_PATH = Path(r"D:\new project\tfl_data.db")

with sqlite3.connect(DB_PATH) as connection:
    fact_arrivals = pd.read_sql_query("SELECT * FROM fact_arrivals", connection)
    dim_line = pd.read_sql_query("SELECT * FROM dim_line", connection)
    dim_station = pd.read_sql_query("SELECT * FROM dim_station", connection)
    dim_time = pd.read_sql_query("SELECT * FROM dim_time", connection)
