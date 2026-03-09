# main.py
# City Congestion Tracker API: Supabase (congestion_readings) + AI insight.
# Run: uvicorn api.main:app --host 0.0.0.0 --port 8000

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env: prefer midterm_pipeline/.env (parent of api/)
api_dir = Path(__file__).resolve().parent
pipeline_root = api_dir.parent
env_path = pipeline_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
elif (api_dir / ".env").exists():
    load_dotenv(api_dir / ".env")

from supabase import create_client, Client

app = FastAPI(title="City Congestion Tracker API", description="Congestion data from Supabase + AI insights")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
AI_BACKEND = (os.getenv("AI_BACKEND") or "ollama_cloud").strip().lower()
OLLAMA_API_KEY = (os.getenv("OLLAMA_API_KEY") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=503, detail="SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


class InsightRequest(BaseModel):
    data_summary: str


# --- Endpoints ---

@app.get("/")
def root():
    return {
        "message": "City Congestion Tracker API",
        "docs": "/docs",
        "health": "/health",
        "readings": "GET /readings (location=, days=, min_level=, max_level=)",
        "insight": "POST /insight",
    }


@app.get("/health")
def health():
    return {"status": "ok", "ai_backend": AI_BACKEND}


@app.get("/readings")
def get_readings(
    location: str | None = None,
    days: int | None = None,
    min_level: int | None = None,
    max_level: int | None = None,
    limit: int = 200,
):
    """Fetch congestion readings from Supabase. Filter by location, last N days, congestion level (1–5)."""
    try:
        sb = get_supabase()
        q = sb.table("congestion_readings").select("*").order("recorded_at", desc=True).limit(limit)
        if location:
            q = q.eq("location_name", location)
        if min_level is not None:
            q = q.gte("congestion_level", min_level)
        if max_level is not None:
            q = q.lte("congestion_level", max_level)
        r = q.execute()
        data = r.data or []
        if days is not None and days > 0:
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            data = [row for row in data if (row.get("recorded_at") or "") >= cutoff]
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase error: {str(e)}")


@app.post("/insight")
def post_insight(body: InsightRequest):
    """Send congestion data summary to AI for narrative insight (worst areas, comparison to usual, etc.)."""
    if AI_BACKEND == "openai":
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set")
        return _openai_insight(body.data_summary)
    if AI_BACKEND == "ollama_cloud":
        if not OLLAMA_API_KEY:
            raise HTTPException(status_code=503, detail="OLLAMA_API_KEY not set")
        return _ollama_cloud_insight(body.data_summary)
    raise HTTPException(status_code=503, detail=f"Unknown AI_BACKEND: {AI_BACKEND}")


CONGESTION_SYSTEM = (
    "You are a city transportation analyst. Use only the congestion data provided. "
    "Congestion level 1 = free flow, 5 = severe. Give a short, actionable summary in markdown: "
    "which locations are worst now, how this period compares to usual, what to watch next, and which roads to avoid."
)


def _ollama_cloud_insight(data_summary: str) -> dict:
    # Ollama Cloud: https://docs.ollama.com/cloud — use a cloud model (e.g. gpt-oss:20b, gpt-oss:120b)
    url = "https://ollama.com/api/chat"
    model = os.getenv("OLLAMA_CLOUD_MODEL", "gpt-oss:20b")
    messages = [
        {"role": "system", "content": CONGESTION_SYSTEM},
        {"role": "user", "content": f"Congestion data:\n\n{data_summary}"},
    ]
    body = {"model": model, "messages": messages, "stream": False}
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
    with httpx.Client(timeout=120) as client:
        resp = client.post(url, headers=headers, json=body)
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "").strip()
    return {"insight": content}


def _openai_insight(data_summary: str) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    messages = [
        {"role": "system", "content": CONGESTION_SYSTEM},
        {"role": "user", "content": f"Congestion data:\n\n{data_summary}"},
    ]
    body = {"model": "gpt-4o-mini", "messages": messages}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    with httpx.Client(timeout=120) as client:
        resp = client.post(url, headers=headers, json=body)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    return {"insight": content}
