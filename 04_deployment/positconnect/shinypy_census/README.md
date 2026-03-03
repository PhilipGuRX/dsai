# Market Analysis — Census + AI (Shiny for Python)

This app is a **market analysis tool** using Census demographics and AI (Ollama or OpenAI). It generates demographic profiles for any location (all states, one state, or counties in a state) and uses an LLM to produce **AI-driven insights**: opportunities and risks for businesses. Adapted for **Posit Connect Cloud**.

## Features

- **Location**: Choose **All states**, **One state**, or **Counties in one state** to scope the analysis.
- **Demographic profile**: Table of Census 2022 ACS 5-year data — population, median age, median household income, median home value.
- **AI market insights**: Ollama (default) or OpenAI generates a short report with (1) demographic summary, (2) 3–5 business opportunities, (3) 3–5 risks. Use only numbers from the data.

## Deploy on Posit Connect (GitHub Actions)

This folder is deployed to Posit Connect via the workflow `.github/workflows/deploy-shinypy.yml` when you push to `main`. Ensure repo secrets `CONNECT_SERVER` and `CONNECT_API_KEY` are set.

Under **Settings** → **Variables** on Connect, add:

| Variable          | Purpose |
|-------------------|--------|
| `CENSUS_API_KEY` or `TEST_API_KEY` | Census API key (optional; 500 req/day without). |
| `AI_BACKEND`      | `ollama_cloud` (default) or `openai`. |
| `OLLAMA_API_KEY`  | Required for Ollama Cloud summaries. |
| `OPENAI_API_KEY`  | Required if `AI_BACKEND=openai`. |

## Optional: Generate manifest locally

From the **repository root** run:

```bash
./04_deployment/positconnect/shinypy_census/manifestme.sh
```

## Files

- **`app.py`** – Shiny for Python app (Census + AI).
- **`requirements.txt`** – Python dependencies.
- **`manifest.json`** – Posit Connect manifest (refresh with manifestme.sh).
- **`manifestme.sh`** – Script to generate `manifest.json` from repo root.
