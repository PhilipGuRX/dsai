# U.S. Census Bureau Data API for Data Science

> Free, public API for demographic and socioeconomic data. Use it to build reporters, visualizations, and analysis pipelines.

---

## 📋 Overview

The **U.S. Census Bureau Data API** provides access to census surveys, including the **American Community Survey (ACS)** and decennial census. Data is returned as JSON, suitable for scripting in Python or R. No API key is required for up to 500 requests per day; a key raises rate limits.

**Use cases:** State and county population, income, housing, education, and other demographic variables by geography and year.

---

## 🔧 Setup

### Get an API Key (Optional)

1. Visit [Census API Key Signup](https://api.census.gov/data/key_signup.html)
2. Enter email and submit
3. Add the key to your project `.env`:

   ```bash
   TEST_API_KEY=your_key_here
   ```

### Install Dependencies

```bash
pip install requests python-dotenv
```

---

## 🚀 Usage

### Example: State Population (ACS 5-year)

```python
import requests

url = "https://api.census.gov/data/2022/acs/acs5"
params = {
    "get": "NAME,B01001_001E",
    "for": "state:01,02,06",  # AL, AK, CA
}
resp = requests.get(url, params=params, timeout=15)
data = resp.json()
```

Response: first row is column names, remaining rows are data.

---

## 📦 Data Structure

### Common Variables

| Variable        | Description                    |
|----------------|--------------------------------|
| `NAME`         | Geography name                 |
| `B01001_001E`  | Total population estimate      |
| `state`        | 2-digit FIPS state code        |
| `county`       | 3-digit FIPS county code       |

### Geography Filters

| Parameter | Example       | Meaning              |
|-----------|---------------|----------------------|
| `for=state:*` | All states | Nationwide           |
| `for=state:06` | California | Single state         |
| `for=county:*` `in=state:06` | All counties in CA | County-level |

---

## ⚠️ Troubleshooting

| Issue          | Action                                  |
|----------------|-----------------------------------------|
| 403 Forbidden  | Check API key and rate limits           |
| Invalid Key    | Ensure `TEST_API_KEY` is correct in `.env` |
| Empty response | Verify `get` and `for` parameters       |

---

## 🔗 Related

- [Census API Documentation](https://www.census.gov/data/developers/data-sets.html)
- [`my_good_query.py`](my_good_query.py) — Full working example with error handling
- [LAB_your_good_api_query.md](LAB_your_good_api_query.md) — Lab assignment

---

← 🏠 [Back to Top](#u-s-census-bureau-data-api-for-data-science)
