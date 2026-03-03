# app.py
# Market analysis tool: Census demographics + AI-driven insights (Ollama / OpenAI).
# Pairs with 03_query_ai. Deploy on Posit Connect Cloud or DigitalOcean.
#
# Generates demographic profiles for any location (states or counties) and uses
# an LLM to summarize opportunities and risks for businesses. Set AI_BACKEND
# and API keys in Posit Connect Cloud Settings >> Variables (or .env locally).

import html
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from shinywidgets import render_plotly
    HAS_PLOTLY = True
except ImportError:
    px = None
    go = None
    render_plotly = None
    HAS_PLOTLY = False

try:
    import faicons as fa
    ICONS = {
        "people": fa.icon_svg("user", "regular"),
        "income": fa.icon_svg("wallet"),
        "housing": fa.icon_svg("dollar-sign"),
    }
except ImportError:
    fa = None
    ICONS = {"people": None, "income": None, "housing": None}

# Optional .env loading for local dev.
# 1) Load a .env next to this file (shinypy_census/.env), if present.
# 2) Also look for a shared project-level .env (the course-wide one in dsai/).
app_dir = Path(__file__).resolve().parent
local_env = app_dir / ".env"
if local_env.exists():
    load_dotenv(local_env)

# Walk up a few parents to find the shared dsai/.env, without reading anything else.
for parent in app_dir.parents:
    candidate = parent / ".env"
    if candidate.exists():
        load_dotenv(candidate)
        break

# Census API key (optional; 500 req/day without). Posit: CENSUS_API_KEY or TEST_API_KEY.
API_KEY = (os.getenv("CENSUS_API_KEY") or os.getenv("TEST_API_KEY") or "").strip()
# AI backend: "ollama" (local), "ollama_cloud", or "openai". Default Ollama for summaries.
AI_BACKEND = (os.getenv("AI_BACKEND") or "ollama_cloud").strip().lower()
OLLAMA_API_KEY = (os.getenv("OLLAMA_API_KEY") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# Census API — 2022 ACS 5-year. Demographics: pop, median age, median income, median home value.
BASE_URL = "https://api.census.gov/data/2022/acs/acs5"
# Variables: B01001_001E=population, B01002_001E=median age, B19013_001E=median HH income, B25077_001E=median home value
CENSUS_VARS = "NAME,B01001_001E,B01002_001E,B19013_001E,B25077_001E"

# All US states + DC for location selector (FIPS code -> name).
STATE_CHOICES = [
    ("01", "Alabama"), ("02", "Alaska"), ("04", "Arizona"), ("05", "Arkansas"),
    ("06", "California"), ("08", "Colorado"), ("09", "Connecticut"), ("10", "Delaware"),
    ("11", "District of Columbia"), ("12", "Florida"), ("13", "Georgia"), ("16", "Idaho"),
    ("17", "Illinois"), ("18", "Indiana"), ("19", "Iowa"), ("20", "Kansas"), ("21", "Kentucky"),
    ("22", "Louisiana"), ("23", "Maine"), ("24", "Maryland"), ("25", "Massachusetts"),
    ("26", "Michigan"), ("27", "Minnesota"), ("28", "Mississippi"), ("29", "Missouri"),
    ("30", "Montana"), ("31", "Nebraska"), ("32", "Nevada"), ("33", "New Hampshire"),
    ("34", "New Jersey"), ("35", "New Mexico"), ("36", "New York"), ("37", "North Carolina"),
    ("38", "North Dakota"), ("39", "Ohio"), ("40", "Oklahoma"), ("41", "Oregon"),
    ("42", "Pennsylvania"), ("44", "Rhode Island"), ("45", "South Carolina"), ("46", "South Dakota"),
    ("47", "Tennessee"), ("48", "Texas"), ("49", "Utah"), ("50", "Vermont"),
    ("51", "Virginia"), ("53", "Washington"), ("54", "West Virginia"), ("55", "Wisconsin"), ("56", "Wyoming"),
]

# --- Census fetch: demographics for state-level or county-level ---

def _safe_int(val):
    """Parse Census value to int; return None if missing or invalid."""
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def fetch_census_demographics(geo_mode, state_code=None):
    """
    Fetch demographic profile from Census API.
    geo_mode: "all_states" | "one_state" | "counties"
    state_code: required when geo_mode is "one_state" or "counties".
    Returns list of dicts: name, population, median_age, median_income, median_home_value, state, (county).
    """
    params = {"get": CENSUS_VARS}
    if API_KEY:
        params["key"] = API_KEY
    headers = {"User-Agent": "SYSEN5381-dsai-market/1.0"}

    if geo_mode == "all_states":
        params["for"] = "state:*"
    elif geo_mode == "one_state" and state_code:
        params["for"] = f"state:{state_code}"
    elif geo_mode == "counties" and state_code:
        params["for"] = "county:*"
        params["in"] = f"state:{state_code}"
    else:
        return []

    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    if not raw or len(raw) < 2:
        return []

    header = raw[0]
    rows = raw[1:]
    # Header order: NAME, B01001_001E, B01002_001E, B19013_001E, B25077_001E, state, [county]
    idx = {h: i for i, h in enumerate(header)}
    out = []
    for row in rows:
        name = (row[idx.get("NAME", 0)] or "").strip()
        pop = _safe_int(row[idx.get("B01001_001E", 1)])
        med_age = _safe_int(row[idx.get("B01002_001E", 2)])
        med_inc = _safe_int(row[idx.get("B19013_001E", 3)])
        med_home = _safe_int(row[idx.get("B25077_001E", 4)])
        state = (row[idx["state"]] or "").strip() if "state" in idx and len(row) > idx["state"] else ""
        county = (row[idx["county"]] or "").strip() if "county" in idx and len(row) > idx["county"] else ""
        out.append({
            "name": name,
            "population": pop or 0,
            "median_age": med_age,
            "median_income": med_inc,
            "median_home_value": med_home,
            "state": state,
            "county": county,
        })
    out.sort(key=lambda x: (x["population"] or 0), reverse=True)
    return out


def format_demographics_for_prompt(records):
    """Format demographic table for LLM market analysis."""
    lines = [
        "Demographic data (2022 ACS 5-year). Use only these numbers.",
        "| Location | Population | Median age | Median HH income ($) | Median home value ($) |",
        "|----------|------------|------------|------------------------|------------------------|",
    ]
    for r in records:
        age = r.get("median_age") if r.get("median_age") is not None else "—"
        inc = f"{r['median_income']:,}" if r.get("median_income") is not None else "—"
        home = f"{r['median_home_value']:,}" if r.get("median_home_value") is not None else "—"
        lines.append(f"| {r['name']} | {r['population']:,} | {age} | {inc} | {home} |")
    return "\n".join(lines)


# --- Market analysis: AI prompt for opportunities and risks ---

MARKET_SYSTEM = (
    "You are a market analyst and community planner. "
    "Reply only in markdown. Be concise. Use only numbers from the data. "
    "Identify concrete everyday-life suggestions for residents and specific commercial opportunities "
    "and risks for businesses; avoid generic filler."
)
MARKET_PROMPT_TEMPLATE = """Using the demographic data below, write a short market and lifestyle analysis.

Requirements (use only numbers from the data):
1. **Demographic profile** — 1–2 sentences: key stats (population, age, income, housing).
2. **Everyday life suggestions** — 3–5 bullet points with practical ideas for people living in this area
   (services to seek out, community programs, housing or commuting considerations), citing the numbers.
3. **Commercial opportunities** — 3–5 bullet points suggesting specific business types or services that
   could work well here, with explicit numeric justification.
4. **Risks / constraints** — 3–5 bullet points on demographic or economic risks, again citing numbers.

Data:
---
{data}
---"""


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
        return "Error: OLLAMA_API_KEY not set. Set it in Posit Connect Cloud Settings >> Variables for Ollama Cloud."
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
        return "Error: OPENAI_API_KEY not set. Set it in Posit Connect Cloud Settings >> Variables for OpenAI."
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


def get_market_insights(data_blob):
    """Call configured AI backend (Ollama default) for market analysis."""
    user_prompt = MARKET_PROMPT_TEMPLATE.format(data=data_blob)
    if AI_BACKEND == "ollama":
        full_prompt = f"{MARKET_SYSTEM}\n\n{user_prompt}"
        return query_ollama_local(full_prompt)
    if AI_BACKEND == "ollama_cloud":
        return query_ollama_cloud(user_prompt, system=MARKET_SYSTEM)
    if AI_BACKEND == "openai":
        return query_openai(user_prompt, system=MARKET_SYSTEM)
    return f"Unknown AI_BACKEND: {AI_BACKEND}. Set to ollama_cloud or openai in Settings >> Variables."


# --- Shiny UI ---

from shiny import reactive, render
from shiny.express import input, ui

ui.page_opts(title="Market Analysis — Census + AI", fillable=True)

with ui.sidebar(open="desktop"):
    ui.h5("Location")
    ui.input_select(
        "geo_mode",
        "Geography",
        choices={
            "all_states": "All states",
            "one_state": "One state",
            "counties": "Counties in one state",
        },
        selected="all_states",
    )
    ui.input_select(
        "state_code",
        "State",
        choices={code: name for code, name in STATE_CHOICES},
        selected="36",
    )
    ui.hr()
    ui.input_action_button("run", "Run market analysis", class_="btn-primary")
    ui.p("Fetches Census demographics for the selected area and generates AI-driven everyday-life and commercial insights.")
    ui.hr()
    ui.p(ui.strong("AI backend: "), AI_BACKEND)
    ui.p("For Ollama Cloud, set AI_BACKEND='ollama_cloud' and OLLAMA_API_KEY in Settings >> Variables.")
    ui.hr()
    ui.p(ui.strong("Charts: "), "On" if HAS_PLOTLY else "Off (install plotly, shinywidgets)")


def _empty_figure(message="Run market analysis to load data."):
    """Return a simple Plotly figure with a message when no data is available."""
    if not HAS_PLOTLY or go is None:
        return None
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=14),
    )
    fig.update_layout(height=280, margin=dict(l=40, r=40, t=40, b=40), xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


@reactive.calc
def analysis_result():
    """Run Census + AI market analysis when button is clicked."""
    if input.run() == 0:
        return {"error": None, "records": [], "summary": "", "ran": False}
    geo = input.geo_mode()
    state = input.state_code()
    if geo != "all_states" and not state:
        return {"error": "Select a state.", "records": [], "summary": "", "ran": True}
    with ui.Progress(min=0, max=3) as p:
        p.set(1, message="Fetching Census demographics…")
        try:
            records = fetch_census_demographics(geo, state_code=state if geo != "all_states" else None)
        except requests.RequestException as e:
            return {"error": str(e), "records": [], "summary": "", "ran": True}
        if not records:
            return {"error": "No data returned for this geography.", "records": [], "summary": "", "ran": True}
        data_blob = format_demographics_for_prompt(records)
        p.set(2, message="Generating AI market insights (Ollama/OpenAI)…")
        try:
            summary = get_market_insights(data_blob)
        except Exception as e:
            summary = f"AI error: {e}"
        p.set(3, message="Done.")
    return {"error": None, "records": records, "summary": summary, "ran": True}


with ui.layout_columns(fill=False):
    with ui.value_box(showcase=ICONS["people"]):
        "Total population (selected)"

        @render.text
        def total_population():
            res = analysis_result()
            if not res["records"]:
                return "—"
            total = sum((r.get("population") or 0) for r in res["records"])
            return f"{total:,}"

    with ui.value_box(showcase=ICONS["income"]):
        "Median household income"

        @render.text
        def median_income_box():
            res = analysis_result()
            if not res["records"]:
                return "—"
            raw = pd.DataFrame(res["records"])
            vals = raw["median_income"].dropna()
            if vals.empty:
                return "—"
            return f"${int(vals.median()):,}"

    with ui.value_box(showcase=ICONS["housing"]):
        "Median home value"

        @render.text
        def median_home_box():
            res = analysis_result()
            if not res["records"]:
                return "—"
            raw = pd.DataFrame(res["records"])
            vals = raw["median_home_value"].dropna()
            if vals.empty:
                return "—"
            return f"${int(vals.median()):,}"


# Demographic profile table and chart
_cols = [7, 5] if HAS_PLOTLY else [12]
with ui.layout_columns(col_widths=_cols):
    with ui.card():
        ui.card_header("Demographic profile (2022 ACS 5-year)")

        @render.data_frame
        def demo_table():
            res = analysis_result()
            if not res["records"]:
                return render.DataGrid(pd.DataFrame(), height="200px")
            raw = pd.DataFrame(res["records"])
            display = pd.DataFrame()
            display["Location"] = raw["name"]
            display["Population"] = raw["population"].apply(lambda x: f"{x:,}" if pd.notna(x) else "—")
            display["Median age"] = raw["median_age"].apply(lambda x: str(x) if pd.notna(x) else "—")
            display["Median income"] = raw["median_income"].apply(lambda x: f"${x:,}" if pd.notna(x) else "—")
            display["Median home value"] = raw["median_home_value"].apply(
                lambda x: f"${x:,}" if pd.notna(x) else "—"
            )
            return render.DataGrid(display, height="300px")

    if HAS_PLOTLY:
        with ui.card():
            ui.card_header("Income vs home value (selected locations)")

            @render_plotly
            def income_home_chart():
                try:
                    res = analysis_result()
                    if not res["records"]:
                        return _empty_figure("Run market analysis to see income vs home value.")
                    raw = pd.DataFrame(res["records"])
                    mask = raw["median_income"].notna() & raw["median_home_value"].notna()
                    if not mask.any():
                        return _empty_figure("No income/home value data for this selection.")
                    data = raw.loc[mask].copy()
                    # Trendline needs at least 2 points; skip to avoid OLS errors
                    use_trendline = "ols" if len(data) >= 2 else False
                    fig = px.scatter(
                        data,
                        x="median_income",
                        y="median_home_value",
                        hover_name="name",
                        labels={
                            "median_income": "Median household income ($)",
                            "median_home_value": "Median home value ($)",
                        },
                        trendline=use_trendline,
                    )
                    fig.update_layout(height=320, margin=dict(l=40, r=20, t=40, b=40))
                    return fig
                except Exception as e:
                    return _empty_figure(f"Could not draw chart: {e}")

# Extra visualizations when plotly is available
if HAS_PLOTLY:
    ui.p(ui.strong("Charts"), " — Run market analysis (sidebar) to populate the visualizations below.", class_="text-muted")
    with ui.layout_columns(col_widths=[6, 6]):
        with ui.card():
            ui.card_header("Population by location (top 20)")

            @render_plotly
            def population_bars():
                try:
                    res = analysis_result()
                    if not res["records"]:
                        return _empty_figure("Run market analysis to see population by location.")
                    raw = pd.DataFrame(res["records"])
                    top = raw.nlargest(20, "population")
                    top = top.sort_values("population", ascending=True)
                    fig = px.bar(
                        top,
                        x="population",
                        y="name",
                        orientation="h",
                        labels={"population": "Population", "name": ""},
                        text="population",
                    )
                    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                    fig.update_layout(height=400, margin=dict(l=10, r=40, t=20, b=40), showlegend=False)
                    return fig
                except Exception as e:
                    return _empty_figure(f"Could not draw chart: {e}")

        with ui.card():
            ui.card_header("Median household income by location (top 20)")

            @render_plotly
            def income_bars():
                try:
                    res = analysis_result()
                    if not res["records"]:
                        return _empty_figure("Run market analysis to see income by location.")
                    raw = pd.DataFrame(res["records"]).dropna(subset=["median_income"])
                    if raw.empty:
                        return _empty_figure("No income data for this selection.")
                    top = raw.nlargest(20, "median_income")
                    top = top.sort_values("median_income", ascending=True)
                    fig = px.bar(
                        top,
                        x="median_income",
                        y="name",
                        orientation="h",
                        labels={"median_income": "Median income ($)", "name": ""},
                        text="median_income",
                    )
                    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
                    fig.update_layout(height=400, margin=dict(l=10, r=60, t=20, b=40), showlegend=False)
                    return fig
                except Exception as e:
                    return _empty_figure(f"Could not draw chart: {e}")

    with ui.layout_columns(col_widths=[12]):
        with ui.card():
            ui.card_header("Distribution of median age across selected locations")

            @render_plotly
            def age_distribution():
                try:
                    res = analysis_result()
                    if not res["records"]:
                        return _empty_figure("Run market analysis to see age distribution.")
                    raw = pd.DataFrame(res["records"])
                    ages = raw["median_age"].dropna()
                    if ages.empty:
                        return _empty_figure("No age data for this selection.")
                    n = len(ages)
                    if n == 1:
                        return _empty_figure("Select multiple locations (e.g. All states or Counties) to see age distribution.")
                    nbins = min(20, max(3, n // 2))
                    fig = px.histogram(
                        x=ages,
                        nbins=nbins,
                        labels={"x": "Median age (years)", "y": "Number of locations"},
                    )
                    fig.update_layout(height=280, margin=dict(l=50, r=20, t=20, b=50))
                    return fig
                except Exception as e:
                    return _empty_figure(f"Could not draw chart: {e}")


# AI-driven market and lifestyle insights
with ui.card():
    ui.card_header("AI market insights — everyday life, opportunities & risks")

    @render.ui
    def insights():
        res = analysis_result()
        if res["error"]:
            return ui.p(res["error"], class_="text-danger")
        if not res["ran"] or not res["records"]:
            return ui.p("Choose a location and click 'Run market analysis'.")
        return ui.HTML(f"<pre style='white-space: pre-wrap;'>{html.escape(res['summary'])}</pre>")
