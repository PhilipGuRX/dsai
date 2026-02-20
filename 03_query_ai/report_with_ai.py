# report_with_ai.py
# API → Process → AI reporting summary
# Pairs with LAB (query API + AI). Uses Census data from 01_query_api/my_good_query.py.
# Tim Fraser
#
# This script (1) fetches state population data from the Census API, (2) cleans and
# aggregates it, (3) formats it for the model, and (4) asks an LLM for a short
# reporting summary. Run from project root: python3 03_query_ai/report_with_ai.py
#
# Prompt iteration and process (Task 3):
# - Start with a clear role ("data analyst") and length ("2-3 sentences" + "5 bullets").
# - Send only aggregated data (totals, top 5, bottom 5) to reduce tokens and focus the model.
# - Refine by tightening format ("exactly 5 bullet points", "at least one number per bullet")
#   so output is consistent. Testing 2-3 runs and then locking the prompt works well.

# 0. SETUP ###################################

## 0.1 Load packages #################################

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

## 0.2 Paths and env ####################################

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
env_path = PROJECT_ROOT / ".env"
try:
    if env_path.exists():
        load_dotenv(env_path)
except (OSError, PermissionError):
    pass  # .env missing or unreadable; use environment or run without keys

# API key for Census (optional; 500 req/day without key)
API_KEY = (os.getenv("TEST_API_KEY") or "").strip()
# AI backend: "ollama" (local), "ollama_cloud", or "openai"
AI_BACKEND = (os.getenv("AI_BACKEND") or "ollama").strip().lower()
OLLAMA_API_KEY = (os.getenv("OLLAMA_API_KEY") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# Census API (same design as 01_query_api/my_good_query.py)
BASE_URL = "https://api.census.gov/data/2022/acs/acs5"
STATE_CODES = "01,02,04,05,06,08,09,10,11,12,13,16,17,18,19,20,21,22,23,24"

# 1. DATA PIPELINE ###################################

## 1.1 Fetch from API ####################################

def fetch_census() -> list:
    """Request state population from Census API. Returns 2D list (header + rows)."""
    params = {"get": "NAME,B01001_001E", "for": f"state:{STATE_CODES}"}
    if API_KEY:
        params["key"] = API_KEY
    headers = {"User-Agent": "SYSEN5381-dsai/1.0"}
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


## 1.2 Process and aggregate ############################

def process_census(raw: list) -> list[dict]:
    """Parse Census response into list of dicts; clean and sort by population."""
    if not raw or len(raw) < 2:
        return []
    header = raw[0]
    rows = raw[1:]
    # Columns: NAME, B01001_001E (population), state
    out = []
    for row in rows:
        name = (row[0] or "").strip()
        try:
            pop = int(row[1]) if row[1] is not None and str(row[1]).strip() != "" else 0
        except (ValueError, TypeError):
            pop = 0
        state = (row[2] or "").strip()
        out.append({"name": name, "population": pop, "state": state})
    # Sort by population descending for reporting
    out.sort(key=lambda x: x["population"], reverse=True)
    return out


def aggregate_for_report(records: list[dict]) -> dict:
    """Compute summary stats for the report (reduces token usage)."""
    if not records:
        return {"total_pop": 0, "n_states": 0, "top5": [], "bottom5": []}
    total = sum(r["population"] for r in records)
    top5 = records[:5]
    bottom5 = records[-5:] if len(records) >= 5 else records
    return {"total_pop": total, "n_states": len(records), "top5": top5, "bottom5": bottom5}


## 1.3 Format for AI #####################################

def format_data_for_prompt(records: list[dict], agg: dict) -> str:
    """Structured text for the model: all states + summary stats."""
    lines = [
        "State population (2022 ACS 5-year). All states:",
        "| State | Population |",
        "|-------|------------|",
    ]
    for r in records:
        lines.append(f"| {r['name']} | {r['population']:,} |")
    lines.extend([
        "",
        f"Total: {agg['total_pop']:,} | n = {agg['n_states']} states.",
    ])
    return "\n".join(lines)


def build_report_md(records: list[dict], agg: dict, ai_summary: str) -> str:
    """Full report as markdown: data table + stats + AI section."""
    lines = [
        "# Census State Population Report",
        "",
        f"*Source: Census API ACS 5-year 2022 | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Data",
        "",
        "| State | Population |",
        "|-------|------------|",
    ]
    for r in records:
        lines.append(f"| {r['name']} | {r['population']:,} |")
    lines.extend([
        "",
        f"**Total:** {agg['total_pop']:,}  \n**States:** {agg['n_states']}",
        "",
        "---",
        "",
        "## Summary",
        "",
        ai_summary.strip(),
        "",
    ])
    return "\n".join(lines)


# 2. AI PROMPT AND REQUEST ###################################

# Prompt: concise, data-first, markdown output. Minimal prose; lead with numbers.

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


def query_ollama_local(prompt: str, model: str = "gemma3:latest") -> str:
    """Send prompt to local Ollama /api/generate. Returns response text."""
    url = "http://localhost:11434/api/generate"
    body = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(url, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def query_ollama_cloud(user_text: str, system: str = "", model: str = "gpt-oss:20b-cloud") -> str:
    """Send messages to Ollama Cloud /api/chat. Returns response text."""
    if not OLLAMA_API_KEY:
        raise ValueError("OLLAMA_API_KEY not set in .env for Ollama Cloud.")
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


def query_openai(user_text: str, system: str = "", model: str = "gpt-4o-mini") -> str:
    """Send messages to OpenAI chat completions. Returns response text."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env for OpenAI.")
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


def get_ai_summary(data_blob: str) -> str:
    """Call the configured AI backend; return markdown summary."""
    user_prompt = USER_PROMPT_TEMPLATE.format(data=data_blob)
    if AI_BACKEND == "ollama":
        # Local Ollama uses a single prompt (no system/user split in /api/generate)
        full_prompt = f"{SYSTEM_INSTRUCTION}\n\n{user_prompt}"
        return query_ollama_local(full_prompt)
    if AI_BACKEND == "ollama_cloud":
        return query_ollama_cloud(user_prompt, system=SYSTEM_INSTRUCTION)
    if AI_BACKEND == "openai":
        return query_openai(user_prompt, system=SYSTEM_INSTRUCTION)
    raise ValueError(f"Unknown AI_BACKEND: {AI_BACKEND}. Use ollama, ollama_cloud, or openai.")


# 3. MAIN ###################################

def main():
    print("\n📊 API → Process → AI report (Census state population)\n")
    print(f"AI backend: {AI_BACKEND}")

    # 1) Fetch and process
    try:
        raw = fetch_census()
    except requests.RequestException as e:
        print(f"Error: Census API request failed: {e}", file=sys.stderr)
        sys.exit(1)
    records = process_census(raw)
    if not records:
        print("Error: No records after processing.", file=sys.stderr)
        sys.exit(1)
    agg = aggregate_for_report(records)
    data_blob = format_data_for_prompt(records, agg)
    print(f"Data: {agg['n_states']} states, total {agg['total_pop']:,}. Requesting AI...", flush=True)

    # 2) Get AI summary
    try:
        summary = get_ai_summary(data_blob)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Error: AI request failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 3) Write deliverable: single markdown file
    report_md = build_report_md(records, agg, summary)
    out_path = SCRIPT_DIR / "report.md"
    out_path.write_text(report_md, encoding="utf-8")
    print(f"Done. Report: {out_path}")


if __name__ == "__main__":
    main()
