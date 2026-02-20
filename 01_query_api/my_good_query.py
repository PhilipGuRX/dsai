# my_good_query.py
# U.S. Census Bureau API – State population (ACS 5-year)
# Pairs with LAB_your_good_api_query.md
# Load API key from .env, request state-level population, document results.
# Run from project root: python3 01_query_api/my_good_query.py

# =============================================================================
# Stage 1: Design Query
# =============================================================================
# API name:     U.S. Census Bureau (https://www.census.gov/data/developers.html)
# Endpoint:     GET /data/2022/acs/acs5 (American Community Survey 5-year)
# Parameters:   get=NAME,B01001_001E (geography name, total population estimate);
#               for=state:01,02,... (FIPS state codes for 20 states).
# Query design: Geographic data – total population for 20 states. Meets
#               requirement of at least 10–20 rows. API key passed as query param key=.
# Expected data: JSON array; first row = column names, remaining rows = data.
#               Columns: NAME, B01001_001E, state.
# =============================================================================

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# --- Load API key from .env (project root) ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
env_path = PROJECT_ROOT / ".env"
try:
    if env_path.exists():
        load_dotenv(env_path)
except (OSError, PermissionError):
    pass  # .env missing or unreadable; use environment or run without key
API_KEY = (os.getenv("TEST_API_KEY") or "").strip()

# Census Data API: ACS 5-year 2022, total population by state (20 states)
BASE_URL = "https://api.census.gov/data/2022/acs/acs5"
# 20 state FIPS codes (AL, AK, AZ, AR, CA, CO, CT, DE, DC, FL, GA, ID, IL, IN, IA, KS, KY, LA, ME, MD)
STATE_CODES = "01,02,04,05,06,08,09,10,11,12,13,16,17,18,19,20,21,22,23,24"


def fetch_census() -> list:
    """Request state population from Census API. Returns 2D list (header + rows)."""
    params = {
        "get": "NAME,B01001_001E",
        "for": f"state:{STATE_CODES}",
    }
    if API_KEY:
        params["key"] = API_KEY
    headers = {"User-Agent": "SYSEN5381-dsai/1.0"}
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    try:
        return resp.json()
    except json.JSONDecodeError as e:
        text = (resp.text or "").strip().lower()
        if resp.status_code == 200 and "invalid key" in text:
            print("Error: Census API returned 'Invalid Key'.", file=sys.stderr)
            print("  - In project root .env set: TEST_API_KEY=your_census_key", file=sys.stderr)
            print("  - No quotes, no spaces. Key from: https://api.census.gov/data/key_signup.html", file=sys.stderr)
        else:
            print(f"Error: API response is not valid JSON: {e}", file=sys.stderr)
            print(f"Response status: {resp.status_code}", file=sys.stderr)
            print(f"Response preview: {(resp.text or '')[:400]!r}", file=sys.stderr)
        raise


def main():
    if not API_KEY:
        print("Warning: TEST_API_KEY not set in .env. Census allows 500 requests/day without a key.", file=sys.stderr)

    try:
        data = fetch_census()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            print("Error: 403 Forbidden. Check TEST_API_KEY in .env.", file=sys.stderr)
        print(f"Error: API request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Error: API request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        sys.exit(1)

    # Census returns first row = column names, rest = data rows
    if not data or len(data) < 2:
        print("Error: No data returned from Census API.", file=sys.stderr)
        sys.exit(1)

    header = data[0]
    rows = data[1:]

    # --- Stage 3: Document Results ---
    n = len(rows)
    print(f"Number of records: {n}")
    print(f"Key fields per record: {header}")
    print(f"Data structure: list of {n} state-level rows (geographic data); "
          "first row is header, each row is [NAME, B01001_001E, state].")

    print("\nAll records:")
    for i, row in enumerate(rows, 1):
        name = row[0] if len(row) > 0 else ""
        pop = row[1] if len(row) > 1 else ""
        state = row[2] if len(row) > 2 else ""
        print(f"  {i}. NAME={name}, B01001_001E={pop}, state={state}")

    return rows


if __name__ == "__main__":
    main()
