# app.py
# Census API + AI report as a Shiny for Python app.
# Pairs with 03_query_ai (report_with_ai.py). Deploy on DigitalOcean App Platform.
# Tim Fraser
#
# This app fetches state population from the Census API, processes it, and
# requests an AI summary. Set AI_BACKEND and API keys in DigitalOcean env.

import html
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# Optional .env (e.g. local dev); on DigitalOcean use app env vars.
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# API key for Census (optional; 500 req/day without key)
API_KEY = (os.getenv("TEST_API_KEY") or "").strip()
# AI backend: "ollama" (local), "ollama_cloud", or "openai"
AI_BACKEND = (os.getenv("AI_BACKEND") or "ollama_cloud").strip().lower()
OLLAMA_API_KEY = (os.getenv("OLLAMA_API_KEY") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# Census API (same as 03_query_ai/report_with_ai.py)
BASE_URL = "https://api.census.gov/data/2022/acs/acs5"
STATE_CODES = "01,02,04,05,06,08,09,10,11,12,13,16,17,18,19,20,21,22,23,24"

# --- Census + AI logic (from 03_query_ai/report_with_ai.py) ---

SYSTEM_INSTRUCTION = (
    "You are a data analyst. Reply only in markdown. Be concise. Use only numbers from the data. No filler."
)
USER_PROMPT_TEMPLATE = """Using the state population data below, write a very short report in markdown.

Requirements:
- One short paragraph (1-2 sentences) with key numbers (largest, total, spread).
- Then 3-5 bullet points; each must include a specific number from the data.
- Use markdown only (no intro text). Be concise; more data, fewer words.

Data:
---
{data}
---"""


def fetch_census():
    """Request state population from Census API. Returns 2D list (header + rows)."""
    params = {"get": "NAME,B01001_001E", "for": f"state:{STATE_CODES}"}
    if API_KEY:
        params["key"] = API_KEY
    headers = {"User-Agent": "SYSEN5381-dsai/1.0"}
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def process_census(raw):
    """Parse Census response into list of dicts; clean and sort by population."""
    if not raw or len(raw) < 2:
        return []
    header = raw[0]
    rows = raw[1:]
    out = []
    for row in rows:
        name = (row[0] or "").strip()
        try:
            pop = int(row[1]) if row[1] is not None and str(row[1]).strip() != "" else 0
        except (ValueError, TypeError):
            pop = 0
        state = (row[2] or "").strip()
        out.append({"name": name, "population": pop, "state": state})
    out.sort(key=lambda x: x["population"], reverse=True)
    return out


def aggregate_for_report(records):
    """Compute summary stats for the report."""
    if not records:
        return {"total_pop": 0, "n_states": 0, "top5": [], "bottom5": []}
    total = sum(r["population"] for r in records)
    top5 = records[:5]
    bottom5 = records[-5:] if len(records) >= 5 else records
    return {"total_pop": total, "n_states": len(records), "top5": top5, "bottom5": bottom5}


def format_data_for_prompt(records, agg):
    """Structured text for the model."""
    lines = [
        "State population (2022 ACS 5-year). All states:",
        "| State | Population |",
        "|-------|------------|",
    ]
    for r in records:
        lines.append(f"| {r['name']} | {r['population']:,} |")
    lines.extend(["", f"Total: {agg['total_pop']:,} | n = {agg['n_states']} states."])
    return "\n".join(lines)


def query_ollama_local(prompt, model="gemma3:latest"):
    """Send prompt to local Ollama /api/generate."""
    url = "http://localhost:11434/api/generate"
    body = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(url, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def query_ollama_cloud(user_text, system="", model="gpt-oss:20b-cloud"):
    """Send messages to Ollama Cloud /api/chat."""
    if not OLLAMA_API_KEY:
        return "Error: OLLAMA_API_KEY not set. Set it in DigitalOcean app env for Ollama Cloud."
    url = "https://ollama.com/api/chat"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_text})
    body = {"model": model, "messages": messages, "stream": False}
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "").strip()


def query_openai(user_text, system="", model="gpt-4o-mini"):
    """Send messages to OpenAI chat completions."""
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY not set. Set it in DigitalOcean app env for OpenAI."
    url = "https://api.openai.com/v1/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_text})
    body = {"model": model, "messages": messages}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def get_ai_summary(data_blob):
    """Call the configured AI backend; return markdown summary."""
    user_prompt = USER_PROMPT_TEMPLATE.format(data=data_blob)
    if AI_BACKEND == "ollama":
        full_prompt = f"{SYSTEM_INSTRUCTION}\n\n{user_prompt}"
        return query_ollama_local(full_prompt)
    if AI_BACKEND == "ollama_cloud":
        return query_ollama_cloud(user_prompt, system=SYSTEM_INSTRUCTION)
    if AI_BACKEND == "openai":
        return query_openai(user_prompt, system=SYSTEM_INSTRUCTION)
    return f"Unknown AI_BACKEND: {AI_BACKEND}. Set AI_BACKEND to ollama_cloud or openai in app env."


# --- Shiny UI ---

from shiny import reactive, render
from shiny.express import input, ui

ui.page_opts(title="Census + AI Report (03_query_ai)", fillable=True)

with ui.sidebar(open="desktop"):
    ui.input_action_button("generate", "Generate report", class_="btn-primary")
    ui.p("Fetches Census state population, then asks an LLM for a short summary.")
    ui.hr()
    ui.p(ui.strong("AI backend: "), AI_BACKEND)
    ui.p("Set AI_BACKEND, OLLAMA_API_KEY or OPENAI_API_KEY in DigitalOcean env.")

@reactive.Calc
def report_result():
    """Run Census + AI pipeline when button is clicked."""
    # Only run after user clicks; initial state is empty
    if input.generate() == 0:
        return {"error": None, "records": [], "agg": None, "summary": "", "ran": False}
    with ui.Progress(min=0, max=3) as p:
        p.set(1, message="Fetching Census…")
        try:
            raw = fetch_census()
        except requests.RequestException as e:
            return {"error": str(e), "records": [], "agg": None, "summary": "", "ran": True}
        records = process_census(raw)
        if not records:
            return {"error": "No records after processing.", "records": [], "agg": None, "summary": "", "ran": True}
        agg = aggregate_for_report(records)
        data_blob = format_data_for_prompt(records, agg)
        p.set(2, message="Requesting AI summary…")
        try:
            summary = get_ai_summary(data_blob)
        except Exception as e:
            summary = f"AI error: {e}"
        p.set(3, message="Done.")
    return {"error": None, "records": records, "agg": agg, "summary": summary, "ran": True}

with ui.card():
    ui.card_header("Data (2022 ACS 5-year state population)")
    @render.data_frame
    def table():
        res = report_result()
        df = pd.DataFrame(res["records"])
        return render.DataGrid(df, height="300px")

with ui.card():
    ui.card_header("AI Summary")
    @render.ui
    def summary():
        res = report_result()
        if res["error"]:
            return ui.p(res["error"], class_="text-danger")
        if not res["ran"] or not res["records"]:
            return ui.p("Click 'Generate report' to run.")
        # Show AI summary (markdown as pre for readability; escape for safe HTML)
        return ui.HTML(f"<pre style='white-space: pre-wrap;'>{html.escape(res['summary'])}</pre>")
