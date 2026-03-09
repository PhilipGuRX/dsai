# City Congestion Tracker — Database → API → Dashboard → AI

**DL Challenge 2026**: A congestion-tracking system that (1) stores congestion-level data in **Supabase**, (2) exposes it via a **REST API**, (3) provides a **dashboard** to explore current or historical congestion and request a summary, and (4) uses **AI** (OpenAI or Ollama Cloud) to turn a slice of data into a short, actionable summary (worst areas, comparison to usual, roads to avoid).

Pipeline: **Supabase (PostgreSQL)** → **REST API (FastAPI)** → **Dashboard (Shiny for Python)** → **AI (OpenAI / Ollama Cloud)**.

## Architecture

```
┌──────────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Supabase        │────▶│  REST API   │────▶│  Dashboard  │────▶│  AI (LLM)   │
│  congestion_     │     │  /readings  │     │  location   │     │  narrative  │
│  readings        │     │  /insight   │     │  time filter│     │  summary    │
└──────────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

- **Supabase**: Table `congestion_readings` (location_name, segment_zone, recorded_at, congestion_level 1–5). Run `supabase/schema.sql` in the SQL Editor.
- **API**: `GET /readings` (filter by location, days, min/max level), `POST /insight` (send data summary, get AI narrative).
- **Dashboard**: Load readings by location and time window; request AI congestion summary.

## Quick start

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. In **SQL Editor**, run the full contents of `supabase/schema.sql` (creates `congestion_readings` and seeds synthetic data).
3. In **Settings → API**, copy **Project URL** and **anon public** key.

### 2. Environment

Copy `.env.example` to `.env` in `midterm_pipeline/` and set `SUPABASE_URL`, `SUPABASE_KEY`, and either `OLLAMA_API_KEY` (with `AI_BACKEND=ollama_cloud`) or `OPENAI_API_KEY` (with `AI_BACKEND=openai`). See **CODEBOOK.md** for all variables.

### 3. API (local)

```bash
cd midterm_pipeline/api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

- **GET** http://localhost:8000/readings — congestion readings (query params: `location`, `days`, `min_level`, `max_level`).
- **POST** http://localhost:8000/insight — body `{"data_summary": "..."}` → AI congestion summary.

### 4. Dashboard (local)

```bash
cd midterm_pipeline/dashboard
pip install -r requirements.txt
shiny run app.py --port 5000
```

Open http://localhost:5000. Choose **Location** and **Time window**, click **Explore** to load data, then **Get AI summary** for an AI narrative.

## Test data

We provide **three** ways to get test data:

1. **`supabase/schema.sql`** — Run in Supabase SQL Editor. Creates the table and inserts 12 synthetic rows (multiple locations and timestamps). This is the main dataset for local runs.
2. **`data/congestion_sample.csv`** — 6 sample rows; same columns as the table. Use for reference or manual import.
3. **`data/congestion_last_24h.csv`** — 6 rows simulating “last 24 hours”; use to test time-window behavior.

See **CODEBOOK.md** for schema and variable descriptions.

## Test executions (demonstration)

Use these to verify the pipeline end-to-end:

1. **All data, ranking and chart**  
   Start API and dashboard. In the dashboard, leave Location = “All locations”, Time window = “Last 7 days”. Click **Explore**. You should see the hero summary, the ranking list, and the congestion chart. Optionally click **Get AI summary**.

2. **Filter by location**  
   Set Location to “Main & 5th”, click **Explore**. The ranking and chart should show only that location; the hero line should name it as the (single) most congested in the selection.

3. **AI summary**  
   With data loaded (e.g. from Test 1), click **Get AI summary**. You should get a short markdown summary (worst areas, comparison, roads to avoid) from the configured AI backend.

## Deployment

- **API**: Deploy to DigitalOcean, Render, etc. Set `SUPABASE_URL`, `SUPABASE_KEY`, `AI_BACKEND`, and `OLLAMA_API_KEY` or `OPENAI_API_KEY` in the environment.
- **Dashboard**: Deploy to Posit Connect (or similar). Set `API_BASE_URL` to your deployed API URL.

## Files

| Path | Description |
|------|-------------|
| `supabase/schema.sql` | `congestion_readings` table, RLS, synthetic inserts. |
| `api/main.py` | FastAPI: `/readings`, `/insight` (congestion-focused AI prompt). |
| `dashboard/app.py` | Shiny: location/time filters, ranking list, chart, AI summary. |
| `data/congestion_sample.csv` | Sample test data (6 rows). |
| `data/congestion_last_24h.csv` | Test data for “last 24h” scenario (6 rows). |
| `CODEBOOK.md` | Schema, API, env vars, and test data files. |
| `.env.example` | Template for environment variables; copy to `.env`. |

## Link to deployed app

- **Dashboard**: [your Posit Connect or DigitalOcean URL — add when deployed]
- **API**: [your API base URL — add when deployed]

If you have not deployed yet, you can still submit the repo; add the links here once the app is live.
