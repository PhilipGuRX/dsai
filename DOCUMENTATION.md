# Documentation — Census API + Web App + AI Reporting

Brief documentation for the data pipeline: API query, Streamlit/Shiny web interface, and AI-powered report generation.

---

## 1. Data Summary

Table summarizing the columns returned by the U.S. Census Bureau API (ACS 5-year state population). The API returns a JSON array; the first row is the header, and each data row has the following columns:

| Column name    | Data type | Description |
|----------------|-----------|-------------|
| `NAME`         | string    | Geography name (e.g., "Alabama", "California", "District of Columbia"). |
| `B01001_001E`  | string*   | Total population estimate for the geography. (*API returns string; app converts to integer/numeric for display and analysis.) |
| `state`        | string    | Two-digit FIPS state code (e.g., "01" = Alabama, "06" = California). Used to filter and identify states. |

*Source:* U.S. Census Bureau Data API, American Community Survey (ACS) 5-year estimates.  
*Typical volume:* 20 state-level rows per request when using the default state FIPS list.

---

## 2. Technical Details

### API keys and environment variables

| Variable          | Where used                    | Required | Description |
|------------------|--------------------------------|----------|-------------|
| `TEST_API_KEY`   | API query, Streamlit app, Shiny app | No       | Census API key. Without it, limit is 500 requests/day. Get one: [Census API Key Signup](https://api.census.gov/data/key_signup.html). |
| `AI_BACKEND`     | Shiny app, `report_with_ai.py` | No       | One of: `ollama` (local), `ollama_cloud`, `openai`. Default in Shiny: `ollama_cloud`. |
| `OLLAMA_API_KEY` | Shiny app, `report_with_ai.py`, `03_ollama_cloud.py` | Yes for Ollama Cloud | For [Ollama Cloud](https://ollama.com) API. |
| `OPENAI_API_KEY` | Shiny app, `report_with_ai.py`, `04_openai.py` | Yes for OpenAI | For OpenAI chat completions. |

Keys are read from a `.env` file in the **project root** (or, for the DigitalOcean Shiny app, from the platform’s environment variables). Never commit `.env`; use `.env.example` or docs to list variable names.

### API endpoint

| Item        | Value |
|------------|--------|
| **API**    | U.S. Census Bureau Data API |
| **Base URL** | `https://api.census.gov/data/{year}/acs/acs5` (e.g. `2022` for ACS 5-year 2022) |
| **Method** | GET |
| **Query params** | `get=NAME,B01001_001E` (variables), `for=state:01,02,...` (FIPS codes), optional `key=<TEST_API_KEY>` |
| **Response** | JSON array: row 0 = header, rows 1+ = data |

### Packages (Python)

- **API script / reporting:** `requests`, `python-dotenv`, `pandas` (for report scripts).
- **Streamlit app** (`02_productivity/app/`): `streamlit`, `requests`, `python-dotenv`, `pandas` (see `02_productivity/app/requirements.txt`).
- **Shiny app** (`04_deployment/digitalocean/shinypy/`): `shiny`, `pandas`, `requests`, `python-dotenv` (see `04_deployment/digitalocean/shinypy/requirements.txt`).

### File structure (main pieces)

```
dsai/
├── .env                          # API keys (do not commit); create from .env.example if provided
├── DOCUMENTATION.md              # This file
├── 01_query_api/
│   └── my_good_query.py          # Standalone Census API query script (LAB 1)
├── 02_productivity/
│   └── app/
│       ├── app.py                # Streamlit app: Census data by year and state (LAB 2)
│       └── requirements.txt      # Dependencies for Streamlit app
├── 03_query_ai/
│   ├── report_with_ai.py         # Census → process → AI summary (Ollama/OpenAI), writes report.md (LAB 3)
│   ├── 03_ollama_cloud.py        # Ollama Cloud API test
│   ├── 04_openai.py              # OpenAI API example
│   └── report.md                 # Generated AI report (after running report_with_ai.py)
└── 04_deployment/
    └── digitalocean/
        └── shinypy/
            ├── app.py            # Shiny for Python: Census + AI report in browser
            └── requirements.txt  # Dependencies for Shiny app
```

---

## 3. Usage Instructions

### Prerequisites

- Python 3.10+ recommended.
- For AI features: either (a) local [Ollama](https://ollama.com) running, or (b) `OLLAMA_API_KEY` for Ollama Cloud, or (c) `OPENAI_API_KEY` for OpenAI.

### Step 1: Clone and go to project root

```bash
cd /path/to/dsai
```

### Step 2: Create `.env` in project root (optional but recommended)

Create a file named `.env` in the project root with:

```env
# Optional: Census API key (500 req/day without it)
TEST_API_KEY=your_census_api_key_here

# For AI report (Shiny app or report_with_ai.py): choose one backend
# AI_BACKEND=ollama
# AI_BACKEND=ollama_cloud
# AI_BACKEND=openai

# If using Ollama Cloud
OLLAMA_API_KEY=your_ollama_cloud_key_here

# If using OpenAI
OPENAI_API_KEY=your_openai_key_here
```

Get keys:

- Census: https://api.census.gov/data/key_signup.html  
- Ollama Cloud: https://ollama.com  
- OpenAI: https://platform.openai.com/api-keys  

### Step 3: Install dependencies

**For the Streamlit app (02_productivity):**

```bash
pip install -r 02_productivity/app/requirements.txt
```

**For the Shiny app (04_deployment):**

```bash
pip install -r 04_deployment/digitalocean/shinypy/requirements.txt
```

**For the API script and AI report script only:**

```bash
pip install requests python-dotenv pandas
```

### Step 4: Run the software

**Run the Streamlit app (Census data by year and state):**

```bash
streamlit run 02_productivity/app/app.py
```

Then open the URL shown (e.g. http://localhost:8501). Use the sidebar to pick ACS year and states; the table updates automatically.

**Run the AI report script (Census → AI summary → report.md):**

```bash
python3 03_query_ai/report_with_ai.py
```

Output: `03_query_ai/report.md`. Set `AI_BACKEND` in `.env` to `ollama`, `ollama_cloud`, or `openai` as needed.

**Run the Shiny app (Census + AI report in browser):**

```bash
cd 04_deployment/digitalocean/shinypy
shiny run app.py
```

Then open the URL shown (e.g. http://127.0.0.1:8000). Click “Generate report” to fetch Census data and get an AI summary.

---

## Quick reference

| Goal                    | Command / action |
|-------------------------|------------------|
| Install Streamlit deps  | `pip install -r 02_productivity/app/requirements.txt` |
| Run Streamlit app      | `streamlit run 02_productivity/app/app.py` |
| Generate AI report     | `python3 03_query_ai/report_with_ai.py` → `03_query_ai/report.md` |
| Run Shiny app          | `cd 04_deployment/digitalocean/shinypy && shiny run app.py` |
| Census key             | In `.env`: `TEST_API_KEY=...` (optional) |
| AI backend             | In `.env`: `AI_BACKEND=ollama` \| `ollama_cloud` \| `openai` |
