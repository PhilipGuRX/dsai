# app.py
# Census State Population – Streamlit App
# Pairs with LAB_cursor_shiny_app.md and 01_query_api/my_good_query.py
# Run from project root: streamlit run 02_productivity/app/app.py

# 0. Setup #################################

## 0.1 Load packages ############################

import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

## 0.2 Load API key from project root .env ###############################

# App lives in 02_productivity/app/; project root is two levels up
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent.parent
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
API_KEY = (os.getenv("TEST_API_KEY") or "").strip()

# Census API configuration
BASE_URL = "https://api.census.gov/data"
# Default 20 state FIPS (AL, AK, AZ, AR, CA, CO, CT, DE, DC, FL, GA, ID, IL, IN, IA, KS, KY, LA, ME, MD)
DEFAULT_STATE_CODES = "01,02,04,05,06,08,09,10,11,12,13,16,17,18,19,20,21,22,23,24"
ACS_YEARS = [2022, 2021, 2020, 2019]


# 1. Helper: fetch Census data ###################################

def fetch_census(year: int, state_codes: str) -> tuple[list | None, str | None]:
    """
    Request state population from Census ACS 5-year API.
    Returns (data, None) on success; (None, error_message) on failure.
    data is 2D list: first row = header, rest = data rows.
    """
    url = f"{BASE_URL}/{year}/acs/acs5"
    params = {
        "get": "NAME,B01001_001E",
        "for": f"state:{state_codes}",
    }
    if API_KEY:
        params["key"] = API_KEY
    headers = {"User-Agent": "SYSEN5381-dsai-streamlit/1.0"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, f"Request failed: {e}"

    try:
        data = resp.json()
    except Exception as e:
        text = (resp.text or "").strip().lower()
        if resp.status_code == 200 and "invalid key" in text:
            return None, (
                "Census API returned 'Invalid Key'. "
                "In project root .env set TEST_API_KEY=your_census_key "
                "(get a key from https://api.census.gov/data/key_signup.html)."
            )
        return None, f"Invalid API response: {e}"

    if not data or len(data) < 2:
        return None, "No data returned from Census API."
    return data, None


# 2. Page config and layout ###################################

st.set_page_config(
    page_title="Census State Population",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a cleaner, modern look
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    h1 { color: #1e3a5f; font-weight: 600; }
    .stMetric { background: #f0f4f8; padding: 0.5rem 1rem; border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #e2e8f0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# 3. Sidebar: query parameters ###################################

st.sidebar.header("Query parameters")
year = st.sidebar.selectbox(
    "ACS 5-year vintage",
    options=ACS_YEARS,
    index=0,
    help="American Community Survey 5-year estimate year.",
)
use_default_states = st.sidebar.checkbox(
    "Use default 20 states",
    value=True,
    help="AL, AK, AZ, AR, CA, CO, CT, DE, DC, FL, GA, ID, IL, IN, IA, KS, KY, LA, ME, MD.",
)
state_codes = DEFAULT_STATE_CODES if use_default_states else st.sidebar.text_input(
    "State FIPS codes (comma-separated)",
    value=DEFAULT_STATE_CODES,
    help="e.g. 01,06,36 for AL, CA, NY.",
)

if not API_KEY:
    st.sidebar.warning("TEST_API_KEY not set in .env. Census allows 500 requests/day without a key.")


# 4. Main area: title and auto-loaded data ###################################

st.title("📊 U.S. Census – State Population")
st.caption("American Community Survey (ACS) 5-year total population estimates by state. Change year or states in the sidebar to refresh.")

# Fetch automatically on load and whenever sidebar inputs change
with st.spinner("Loading data from Census API…"):
    data, err = fetch_census(year, state_codes.strip())

if err:
    st.error(err)
else:
    header = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=header)

    # Rename for display
    df = df.rename(columns={"B01001_001E": "population"})
    df["population"] = pd.to_numeric(df["population"], errors="coerce")

    st.success(f"Retrieved **{len(df)}** records (ACS {year} 5-year).")
    st.metric("Number of states", len(df))
    st.dataframe(
        df[["NAME", "population", "state"]],
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Data structure"):
        st.write("Columns: **NAME** (geography name), **population** (total population estimate), **state** (FIPS code).")
        st.code(f"Records: {len(df)} state-level rows from ACS {year} 5-year.")
