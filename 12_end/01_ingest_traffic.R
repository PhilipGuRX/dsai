#' @name 01_ingest_traffic.R
#' @title Ingest Brussels-area traffic flow into SQLite (metro_id)
#' @author Tim Fraser
#' @description
#' Topic: scheduled traffic ingestion
#'
#' Fetches TomTom Traffic Flow Segment Data for several Brussels coordinates and
#' appends rows to data/traffic.db. Rows are keyed by metro_id (Brussels = 948),
#' not city_id.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

library(DBI) # for database connection
library(httr2) # for HTTP requests
library(jsonlite) # for JSON parsing
library(RSQLite) # for SQLite driver

## 0.2 Working directory #################################

# Resolve paths relative to this script's folder (works from repo root or 12_end).
args = commandArgs(trailingOnly = FALSE)
file_arg = args[startsWith(args, "--file=")]
if (length(file_arg) == 1) {
  this_file = sub("^--file=", "", file_arg[1])
  setwd(dirname(normalizePath(this_file)))
} else if (file.exists(file.path("12_end", "01_ingest_traffic.R")) && !file.exists("01_ingest_traffic.R")) {
  # Sourcing from repo root without --file= (e.g. RStudio Run on a saved file path)
  setwd("12_end")
}

## 0.3 Load local .env (optional) #################################

# readRenviron() does not overwrite variables already set in the shell; parse
# .env ourselves so 12_end/.env always wins (same as the Python ingest script).
if (file.exists(".env")) {
  env_lines = readLines(".env", warn = FALSE, encoding = "UTF-8")
  for (line in env_lines) {
    line = trimws(line)
    if (!nzchar(line) || startsWith(line, "#")) {
      next
    }
    if (!grepl("=", line, fixed = TRUE)) {
      next
    }
    key = trimws(sub("=.*", "", line, perl = TRUE))
    val = trimws(sub("^[^=]*=", "", line, perl = TRUE))
    val = sub("^[\"']", "", sub("[\"']$", "", val))
    if (nzchar(key)) {
      args = list(val)
      names(args) = key
      do.call(Sys.setenv, args)
    }
  }
}

## 0.4 Configuration #################################

# TomTom Traffic Index metro identifier for Brussels (logical key for rows).
METRO_ID = 948L

TOMTOM_API_KEY = Sys.getenv("TOMTOM_API_KEY", unset = "")
if (!nzchar(TOMTOM_API_KEY)) {
  stop("Set TOMTOM_API_KEY in the environment or in 12_end/.env (see ?httr2 and TomTom developer portal).")
}

# Sample points across the Brussels metro (lat, lon), WGS84
BRUSSELS_SAMPLE_POINTS = list(
  c(50.8445, 4.3497),
  c(50.8435, 4.3839),
  c(50.8503, 4.3517),
  c(50.7940, 4.3180),
  c(50.9010, 4.4855),
  c(50.8320, 4.2890)
)

DB_PATH = file.path("data", "traffic.db")
FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

# 1. FETCH AND STORE ###################################

dir.create(dirname(DB_PATH), showWarnings = FALSE, recursive = TRUE)
ingested_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")

con = dbConnect(RSQLite::SQLite(), DB_PATH)
on.exit(dbDisconnect(con), add = TRUE)

dbExecute(con, "
CREATE TABLE IF NOT EXISTS traffic (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  metro_id INTEGER NOT NULL,
  ingested_at TEXT NOT NULL,
  sample_lat REAL NOT NULL,
  sample_lon REAL NOT NULL,
  frc TEXT,
  current_speed REAL,
  free_flow_speed REAL,
  current_travel_time REAL,
  free_flow_travel_time REAL,
  confidence REAL,
  road_closure INTEGER
)
")
dbExecute(con, "CREATE INDEX IF NOT EXISTS idx_traffic_metro_time ON traffic(metro_id, ingested_at)")

rows_written = 0L
for (pt in BRUSSELS_SAMPLE_POINTS) {
  lat = pt[1]
  lon = pt[2]
  point = paste(lat, lon, sep = ",")
  resp = tryCatch(
    request(FLOW_URL) |>
      req_url_query(key = TOMTOM_API_KEY, point = point, unit = "kmph") |>
      req_perform(),
    error = function(e) {
      message("Request failed for ", point, ": ", conditionMessage(e))
      NULL
    }
  )
  if (is.null(resp)) {
    next
  }
  if (resp_status(resp) != 200L) {
    message("HTTP ", resp_status(resp), " for ", point, ": ", resp_body_string(resp))
    next
  }
  payload = resp_body_json(resp, simplifyVector = TRUE)
  if (is.null(payload$flowSegmentData)) {
    message("Unexpected JSON for ", point)
    next
  }
  fsd = payload$flowSegmentData
  road_closure = if (isTRUE(fsd$roadClosure) || identical(fsd$roadClosure, 1L)) 1L else 0L
  dbExecute(
    con,
    "
    INSERT INTO traffic (
      metro_id, ingested_at, sample_lat, sample_lon,
      frc, current_speed, free_flow_speed,
      current_travel_time, free_flow_travel_time,
      confidence, road_closure
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ",
    params = list(
      METRO_ID,
      ingested_at,
      lat,
      lon,
      fsd$frc,
      fsd$currentSpeed,
      fsd$freeFlowSpeed,
      fsd$currentTravelTime,
      fsd$freeFlowTravelTime,
      fsd$confidence,
      road_closure
    )
  )
  rows_written = rows_written + 1L
}

message("Ingest finished: ", rows_written, " rows for metro_id=", METRO_ID, " -> ", DB_PATH)
if (rows_written < 1L) {
  stop("No rows written; refusing success exit for CI.")
}
