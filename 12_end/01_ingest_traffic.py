# 01_ingest_traffic.py
# Ingest Brussels-area traffic flow samples into SQLite (metro_id key)
# Pairs with 01_ingest_traffic.R
# Tim Fraser

# Fetches TomTom Traffic Flow Segment Data for several coordinates in the
# Brussels metro, then appends rows to data/traffic.db keyed by metro_id.

# 0. SETUP ###################################

## 0.1 Load Packages ############################

import json  # for parsing API JSON
import os  # for environment variables and paths
import ssl  # for TLS to TomTom (macOS Python often needs certifi CA bundle)
import sqlite3  # for SQLite database operations (built-in)
import sys  # for stderr messages
import urllib.error  # for HTTP errors
import urllib.parse  # for query string encoding
import urllib.request  # for HTTPS GET without extra dependencies
from datetime import datetime, timezone  # for ingest timestamps
from pathlib import Path  # for portable paths

## 0.2 Working directory ############################

# Always resolve paths relative to this script (so you can run from repo root
# or from inside 12_end/).
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

## 0.3 Load local .env (optional) ############################

ENV_PATH = SCRIPT_DIR / ".env"
if ENV_PATH.exists():
    # Apply every assignment from .env so it wins over stale shell exports
    # (e.g. a leftover `export TOMTOM_API_KEY=your_key_here` from testing).
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ[key] = val

## 0.4 Configuration ############################

# TomTom Traffic Index metro identifier for Brussels (used as the logical key
# for all rows from this script — not city_id).
METRO_ID = 948

# TomTom developer key (set TOMTOM_API_KEY in the environment or in 12_end/.env)
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY", "").strip()

# Sample points across the Brussels metro (lat, lon), WGS84
BRUSSELS_SAMPLE_POINTS = [
    (50.8445, 4.3497),  # Grand Place area
    (50.8435, 4.3839),  # EU institutions quarter
    (50.8503, 4.3517),  # city centre north
    (50.7940, 4.3180),  # south (Forest / Saint-Gilles)
    (50.9010, 4.4855),  # north-east (toward airport corridor)
    (50.8320, 4.2890),  # west (Anderlecht)
]

DB_PATH = SCRIPT_DIR / "data" / "traffic.db"
FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"


def _https_context():
    """TLS context with Mozilla CA bundle via certifi (fixes macOS verify failures)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_flow_segment(lat, lon, api_key):
    """Return parsed JSON from TomTom Flow Segment Data for one point (lat, lon)."""
    point = f"{lat},{lon}"
    qs = urllib.parse.urlencode({"key": api_key, "point": point, "unit": "kmph"})
    url = f"{FLOW_URL}?{qs}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    ctx = _https_context()
    with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_coords(coordinate_block):
    """TomTom returns coordinate as one dict or a list of dicts."""
    if not coordinate_block:
        return []
    coord = coordinate_block.get("coordinate")
    if coord is None:
        return []
    if isinstance(coord, dict):
        return [coord]
    return list(coord)


def main():
    if not TOMTOM_API_KEY:
        print(
            "Set TOMTOM_API_KEY in the environment or in 12_end/.env "
            "(see https://developer.tomtom.com/).",
            file=sys.stderr,
        )
        sys.exit(1)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            """
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
            """
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_traffic_metro_time ON traffic(metro_id, ingested_at)"
        )

        rows_written = 0
        for sample_lat, sample_lon in BRUSSELS_SAMPLE_POINTS:
            try:
                payload = fetch_flow_segment(sample_lat, sample_lon, TOMTOM_API_KEY)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                print(f"HTTP {e.code} for point {sample_lat},{sample_lon}: {body}", file=sys.stderr)
                continue
            except urllib.error.URLError as e:
                print(f"Network error for point {sample_lat},{sample_lon}: {e}", file=sys.stderr)
                continue

            if "flowSegmentData" not in payload:
                print(f"Unexpected payload for {sample_lat},{sample_lon}: {payload}", file=sys.stderr)
                continue

            fsd = payload["flowSegmentData"]
            road_closure = 1 if fsd.get("roadClosure") in (True, "true", 1) else 0
            con.execute(
                """
                INSERT INTO traffic (
                  metro_id, ingested_at, sample_lat, sample_lon,
                  frc, current_speed, free_flow_speed,
                  current_travel_time, free_flow_travel_time,
                  confidence, road_closure
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    METRO_ID,
                    ingested_at,
                    sample_lat,
                    sample_lon,
                    fsd.get("frc"),
                    fsd.get("currentSpeed"),
                    fsd.get("freeFlowSpeed"),
                    fsd.get("currentTravelTime"),
                    fsd.get("freeFlowTravelTime"),
                    fsd.get("confidence"),
                    road_closure,
                ),
            )
            rows_written += 1
            # Touch coordinates only to validate shape (optional observability)
            _ = normalize_coords(fsd.get("coordinates") or {})

        con.commit()
        print(f"Ingest finished: {rows_written} rows for metro_id={METRO_ID} -> {DB_PATH}")
        if rows_written < 1:
            print("No rows written; refusing success exit for CI.", file=sys.stderr)
            sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
