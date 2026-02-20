# Census State Population App

> Streamlit app that runs the Census API query from [`my_good_query.py`](../01_query_api/my_good_query.py) on demand.

---

## 📋 Overview

This app implements the U.S. Census Bureau ACS 5-year state population query from the [LAB_your_good_api_query](../01_query_api/LAB_your_good_api_query.md) lab. Users choose the **ACS vintage year** and **state set** (default 20 states or custom FIPS codes), then click **Fetch data** to run the API and view results in a table.

---

## 🔧 Setup

1. **Python 3.9+** and a virtual environment (recommended).

2. **Install dependencies** from the app folder or project root:

```bash
pip install -r 02_productivity/app/requirements.txt
```

3. **API key (optional):** Census allows 500 requests/day without a key. For a key, add to project root `.env`:

```
TEST_API_KEY=your_census_key
```

Get a key: [Census API Key Signup](https://api.census.gov/data/key_signup.html).

---

## 🚀 Usage

From the **project root** (`dsai/`):

```bash
streamlit run 02_productivity/app/app.py
```

- Use the **sidebar** to set ACS 5-year vintage and state selection.
- Click **Fetch data** to run the query; results appear as a table with record count and data structure notes.
- Errors (e.g. invalid key, no data) are shown in the UI.

---

## 📦 Data Structure

| Column      | Description                          |
|------------|--------------------------------------|
| NAME       | Geography name (e.g. state name)     |
| population | Total population estimate (B01001_001E) |
| state      | FIPS state code                      |

Data is from the [Census Bureau API](https://www.census.gov/data/developers.html), endpoint `GET /data/{year}/acs/acs5`.

---

## 🔗 Related

- Query script: [`01_query_api/my_good_query.py`](../01_query_api/my_good_query.py)
- Lab: [`02_productivity/LAB_cursor_shiny_app.md`](../LAB_cursor_shiny_app.md)
- Context checklist: [`CONTEXT_CHECKLIST.md`](CONTEXT_CHECKLIST.md)

---

## ⚠️ Troubleshooting

- **Invalid Key:** Ensure `TEST_API_KEY` in project root `.env` has no quotes or spaces; key from [key signup](https://api.census.gov/data/key_signup.html).
- **No data:** Check that state FIPS codes in the sidebar are comma-separated and valid (e.g. `01,06,36`).
- **Request failed:** Check network; Census API may be slow or down.
