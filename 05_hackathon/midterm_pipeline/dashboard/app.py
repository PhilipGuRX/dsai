# app.py
# City Congestion Tracker — TomTom Traffic Index style.
# Header + hero card + big readable ranking list. API_BASE_URL or http://localhost:8000.

import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from shiny import reactive, render
from shiny.express import input, ui

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

# Load .env
app_dir = Path(__file__).resolve().parent
pipeline_root = app_dir.parent
env_path = pipeline_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
elif (app_dir / ".env").exists():
    load_dotenv(app_dir / ".env")

API_BASE = (os.getenv("API_BASE_URL") or "http://localhost:8000").rstrip("/")
CITY_NAME = os.getenv("CITY_NAME", "Metro City")

ui.page_opts(title=f"Congestion Index — {CITY_NAME}", fillable=False)

# TomTom-like: dark header, readable ranking list
ui.tags.style(
    "html, body { overflow-y: auto !important; min-height: 100vh; }\n"
    ".congestion-header { background: #2c3e50; color: #ecf0f1; padding: 0.75rem 1.5rem; "
    "display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem; }\n"
    ".congestion-header .brand { font-size: 1.25rem; font-weight: 700; }\n"
    ".congestion-header .filters { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }\n"
    ".congestion-header label { margin: 0 0.25rem 0 0; color: #bdc3c7; font-size: 0.9rem; }\n"
    ".congestion-header .btn-explore { background: #e74c3c; color: white; border: none; font-weight: 600; }\n"
    ".hero-card { max-width: 720px; margin: 2rem auto; padding: 2rem; border-radius: 12px; "
    "box-shadow: 0 4px 20px rgba(0,0,0,0.08); background: white; }\n"
    ".hero-card h2 { color: #2c3e50; margin-bottom: 0.5rem; }\n"
    ".ranking-list { list-style: none; padding: 0; margin: 1rem 0 0 0; }\n"
    ".ranking-list li { padding: 0.75rem 1rem; margin-bottom: 0.5rem; border-radius: 8px; "
    "background: #f8f9fa; font-size: 1.1rem; display: flex; align-items: center; gap: 1rem; }\n"
    ".ranking-list .rank-badge { min-width: 2rem; height: 2rem; border-radius: 50%; "
    "display: inline-flex; align-items: center; justify-content: center; font-weight: 700; "
    "color: white; font-size: 0.9rem; }\n"
    ".ranking-list .rank-1 { background: #e74c3c; }\n"
    ".ranking-list .rank-2 { background: #e67e22; }\n"
    ".ranking-list .rank-3 { background: #f39c12; }\n"
    ".ranking-list .rank-4, .ranking-list .rank-5 { background: #95a5a6; }\n"
    ".ranking-list .pct { margin-left: auto; font-weight: 600; color: #2c3e50; }\n"
)

# --- Top bar (TomTom-style header) ---
with ui.tags.div(class_="congestion-header"):
    ui.tags.span("Congestion Index", class_="brand")
    ui.tags.span(" | ", class_="text-muted")
    ui.tags.span(CITY_NAME, class_="brand")
    with ui.tags.div(class_="filters"):
        ui.input_select(
            "location",
            "Location",
            choices={
                "": "All locations",
                "Main & 5th": "Main & 5th",
                "Highway 101 @ Exit 12": "Highway 101 @ Exit 12",
                "Downtown Plaza": "Downtown Plaza",
                "River Bridge South": "River Bridge South",
                "Airport Access Rd": "Airport Access Rd",
            },
            selected="",
            width="180px",
        )
        ui.input_select(
            "days",
            "Time window",
            choices={"": "All time", "7": "Last 7 days", "3": "Last 3 days", "1": "Last 1 day"},
            selected="7",
            width="140px",
        )
        ui.input_action_button("load_data", "Explore", class_="btn-explore")

# --- Main content ---
with ui.tags.div(class_="container-fluid", style="padding: 0 1.5rem 2rem;"):
    # Hero card: "Find meaning in movement"
    with ui.tags.div(class_="hero-card"):
        ui.tags.h2("Find meaning in movement")
        ui.tags.p(
            f"The Congestion Index lets you see patterns in {CITY_NAME}. "
            "Choose location and time window above, then click Explore.",
            class_="text-muted",
            style="margin-bottom: 1rem;",
        )

        @render.ui
        def hero_finding():
            s = summary_stats()
            if not s or not s.get("comparison"):
                return ui.tags.p("Click Explore to load congestion data.", class_="text-muted mb-0")
            loc = s.get("worst_location") or ""
            pct = s.get("avg_pct")
            pct_str = f" ({pct}% avg congestion)" if pct is not None else ""
            return ui.tags.div(
                ui.tags.p(
                    f"In the selected period, {loc} was the most congested location in {CITY_NAME}{pct_str}.",
                    style="font-size: 1.15rem; font-weight: 500; margin-bottom: 0;",
                ),
                class_="mb-0",
            )

    # Ranking as a big readable list (like TomTom's 1. DC 42%, 2. Hawai'i 32%)
    with ui.tags.div(class_="hero-card", style="margin-top: 1.5rem;"):
        ui.tags.h4(f"Ranking — Most congested locations in {CITY_NAME}", style="margin-bottom: 0.5rem;")
        ui.tags.p("Locations ranked by average congestion. Clear, at a glance.", class_="text-muted small mb-3")

        @render.ui
        def ranking_list():
            s = summary_stats()
            rdf = s.get("ranking_df") if s else None
            if rdf is None or (isinstance(rdf, pd.DataFrame) and rdf.empty):
                return ui.tags.p("Load data with Explore to see the ranking.", class_="text-muted")
            df = rdf
            items = []
            for _, row in df.iterrows():
                r = int(row["rank"])
                loc = str(row["location_name"])
                pct = row["avg_pct"]
                rank_class = f"rank-{min(r, 5)}"
                items.append(
                    ui.tags.li(
                        ui.tags.span(str(r), class_=f"rank-badge {rank_class}"),
                        ui.tags.span(loc),
                        ui.tags.span(f"{pct}%", class_="pct"),
                    )
                )
            return ui.tags.ul(*items, class_="ranking-list")

    # Chart
    if HAS_PLOTLY:
        with ui.card(full_screen=True, style="margin-top: 1.5rem;"):
            ui.tags.h4(f"Congestion by location in {CITY_NAME}")
            ui.tags.p("Average congestion %. Expand (↗) for larger view.", class_="text-muted small")

            @render_plotly
            def congestion_chart():
                s = summary_stats()
                rdf = s.get("ranking_df") if s else None
                if rdf is None or (isinstance(rdf, pd.DataFrame) and rdf.empty):
                    fig = go.Figure()
                    fig.add_annotation(text="Click Explore to see chart", x=0.5, y=0.5, showarrow=False)
                    fig.update_layout(height=260, margin=dict(l=40, r=40), xaxis=dict(visible=False), yaxis=dict(visible=False))
                    return fig
                df = rdf
                fig = px.bar(df, x="location_name", y="avg_pct", labels={"location_name": "Location", "avg_pct": "Avg congestion %"})
                fig.update_layout(height=260, margin=dict(l=40, r=40), xaxis_tickangle=-45)
                return fig

    # All readings table (expand for full view)
    with ui.card(full_screen=True, style="margin-top: 1.5rem;"):
        ui.tags.h4("All readings (from API / Supabase)")
        ui.tags.p("Click expand (↗) for full table.", class_="text-muted small")

        @render.data_frame
        def table():
            data = readings_for_table()
            if data is None:
                return pd.DataFrame({"Message": ["Click Explore to fetch readings."]})
            if isinstance(data, dict) and data.get("_error"):
                return pd.DataFrame({"Error": [data["_error"]]})
            if not data:
                return pd.DataFrame({"Message": ["No rows. Try another location or time window."]})
            df = pd.DataFrame(data)
            for col in ("id", "recorded_at", "created_at"):
                if col in df.columns:
                    df[col] = df[col].astype(str)
            return df

    # AI summary
    with ui.card(full_screen=False, style="margin-top: 1.5rem;"):
        ui.tags.h4("AI congestion summary")
        ui.tags.p("Worst areas, comparison to usual, roads to avoid.", class_="text-muted small")
        ui.input_action_button("get_insight", "Get AI summary", class_="btn-primary mt-2")

        @render.ui
        def insight_ui():
            out = insight_result()
            if out is None:
                return ui.tags.p("Click 'Get AI summary' for an actionable narrative.", class_="text-muted mt-2")
            return ui.markdown(out)

# --- Reactive state and logic ---
current_data = reactive.Value(None)


@reactive.effect
def _on_load():
    if input.load_data() == 0:
        return
    try:
        params = {"days": input.days() or None}
        if input.location():
            params["location"] = input.location()
        # Hosted APIs (e.g. Render free tier) may need >30s on cold start
        r = requests.get(f"{API_BASE}/readings", params=params, timeout=120)
        r.raise_for_status()
        current_data.set(r.json())
    except requests.RequestException as e:
        detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                body = e.response.json()
                if isinstance(body.get("detail"), str):
                    detail = body["detail"]
            except Exception:
                pass
        current_data.set({"_error": detail})


@reactive.calc
def readings_for_table():
    return current_data.get()


@reactive.calc
def summary_stats():
    data = current_data.get()
    if data is None or isinstance(data, dict):
        return None
    if not data:
        return {"avg_pct": None, "worst_location": None, "total": 0, "ranking_df": None, "comparison": None}
    df = pd.DataFrame(data)
    if "congestion_level" not in df.columns:
        return {"avg_pct": None, "worst_location": None, "total": len(df), "ranking_df": None, "comparison": None}
    df["pct"] = (df["congestion_level"] - 1) / 4 * 100
    avg_pct = round(df["pct"].mean(), 1)
    by_loc = df.groupby("location_name").agg(
        avg_level=("congestion_level", "mean"),
        max_level=("congestion_level", "max"),
        count=("congestion_level", "count"),
    ).reset_index()
    by_loc["avg_pct"] = ((by_loc["avg_level"] - 1) / 4 * 100).round(1)
    by_loc = by_loc.sort_values("avg_level", ascending=False).reset_index(drop=True)
    by_loc["rank"] = range(1, len(by_loc) + 1)
    worst = by_loc.iloc[0]["location_name"] if len(by_loc) > 0 else None
    comparison = f"In the selected period, {worst} was the most congested location." if worst else None
    return {
        "avg_pct": avg_pct,
        "worst_location": worst,
        "total": len(df),
        "ranking_df": by_loc[["rank", "location_name", "avg_pct", "max_level", "count"]],
        "comparison": comparison,
    }


@reactive.calc
def insight_result():
    if input.get_insight() == 0:
        return None
    data = current_data.get()
    if data is None:
        return "Click Explore first, then 'Get AI summary'."
    if isinstance(data, dict) and data.get("_error"):
        return data["_error"]
    if not data:
        return "No readings. Try another location or time window."
    lines = ["Congestion readings (level 1=free flow, 5=severe):", ""]
    for row in data[:50]:
        loc = row.get("location_name", "")
        zone = row.get("segment_zone", "")
        ts = row.get("recorded_at", "")[:19] if row.get("recorded_at") else ""
        lvl = row.get("congestion_level", "")
        lines.append(f"- {loc} ({zone}): level {lvl} at {ts}")
    summary = "\n".join(lines)
    try:
        r = requests.post(f"{API_BASE}/insight", json={"data_summary": summary}, timeout=120)
        r.raise_for_status()
        return r.json().get("insight", "No insight returned.")
    except requests.RequestException as e:
        return f"API error: {e}"
