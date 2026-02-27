# Market Analysis — Census + AI (Shiny for Python)

This app is a **market analysis tool** using Census demographics and AI (Ollama or OpenAI). It generates demographic profiles for any location (all states, one state, or counties in a state) and uses an LLM to produce **AI-driven insights**: opportunities and risks for businesses. Adapted for **Posit Connect Cloud**.

## Features

- **Location**: Choose **All states**, **One state**, or **Counties in one state** to scope the analysis.
- **Demographic profile**: Table of Census 2022 ACS 5-year data — population, median age, median household income, median home value.
- **AI market insights**: Ollama (default) or OpenAI generates a short report with (1) demographic summary, (2) 3–5 business opportunities, (3) 3–5 risks. Use only numbers from the data.

## Deploy on Posit Connect Cloud

1. Push this repo (including `04_deployment/positconnectcloud/shinypy_census/`) to a **public** GitHub repository.
2. In Posit Connect Cloud: **Publish** → **From Github** → install the GitHub App and authorize the repo.
3. Choose **Shiny** and set the app path to:  
   `04_deployment/positconnectcloud/shinypy_census`
4. Under **Advanced Settings** (or after deploy: **Settings** → **Variables**), add:

   | Variable          | Purpose |
   |-------------------|--------|
   | `CENSUS_API_KEY` or `TEST_API_KEY` | Census API key (optional; 500 req/day without). |
   | `AI_BACKEND`      | `ollama_cloud` (default) or `openai`. |
   | `OLLAMA_API_KEY`  | Required for Ollama Cloud summaries. |
   | `OPENAI_API_KEY`  | Required if `AI_BACKEND=openai`. |

5. Publish. The app will build and install packages from `requirements.txt`.

## Optional: Generate manifest locally

To write a `manifest.json` for this app (e.g. for Connect Server or debugging), from the **repository root** run:

```bash
./04_deployment/positconnectcloud/shinypy_census/manifestme.sh
```

## Files

- **`app.py`** – Shiny for Python app (Census + AI).
- **`requirements.txt`** – Python dependencies (required by Posit Connect Cloud).
- **`manifestme.sh`** – Script to generate `manifest.json` from repo root.
