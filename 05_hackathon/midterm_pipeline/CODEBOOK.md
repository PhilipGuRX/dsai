# Codebook — City Congestion Tracker

## Database schema (Supabase)

Table: **`congestion_readings`**

| Column           | Type        | Description |
|------------------|-------------|-------------|
| `id`             | UUID        | Primary key, auto-generated. |
| `location_name`  | TEXT        | Intersection, segment, or zone name (e.g. "Main & 5th"). |
| `segment_zone`   | TEXT        | Optional area label (e.g. "Downtown", "North Corridor"). |
| `recorded_at`    | TIMESTAMPTZ | When the reading was taken. |
| `congestion_level` | INTEGER   | 1 = free flow, 5 = severe congestion. |
| `created_at`     | TIMESTAMPTZ | Insert time, default `now()`. |

## API

- **GET /readings**: Query params — `location` (filter by location_name), `days` (last N days), `min_level`, `max_level`, `limit`. Returns JSON array of rows.
- **POST /insight**: Request body `{"data_summary": "string"}`. Response `{"insight": "string"}` (markdown from AI: worst areas, comparison to usual, roads to avoid).

## Environment variables

| Variable         | Where used | Purpose |
|------------------|------------|---------|
| `SUPABASE_URL`   | API        | Supabase project URL. |
| `SUPABASE_KEY`   | API        | Supabase anon or service role key. |
| `AI_BACKEND`     | API        | `openai` or `ollama_cloud`. |
| `OLLAMA_API_KEY` | API        | Required if `AI_BACKEND=ollama_cloud`. Create at [ollama.com/settings/keys](https://ollama.com/settings/keys). |
| `OLLAMA_CLOUD_MODEL` | API   | Optional. Cloud model name (default: `gpt-oss:20b`). See [Ollama Cloud models](https://ollama.com/search?c=cloud). |
| `OPENAI_API_KEY` | API        | Required if `AI_BACKEND=openai`. |
| `API_BASE_URL`   | Dashboard  | Base URL of the deployed API (default: http://localhost:8000). |
| `CITY_NAME`      | Dashboard  | City name shown in the UI (default: Metro City). |

## Test data files

| File | Description |
|------|-------------|
| `supabase/schema.sql` | Primary test data: run in SQL Editor to create `congestion_readings` and seed 12 synthetic rows (multiple locations, timestamps, levels 1–5). |
| `data/congestion_sample.csv` | Sample CSV: 6 rows for quick import or reference. Columns: location_name, segment_zone, recorded_at, congestion_level. |
| `data/congestion_last_24h.csv` | Alternative scenario: 6 rows simulating last-24h readings; use to test time-window or “current” views. |
