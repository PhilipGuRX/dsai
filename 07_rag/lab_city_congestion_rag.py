# lab_city_congestion_rag.py
# Custom RAG: City Congestion Tracker reference data (CSV)
# Pairs with SYSEN 5381 midterm pipeline theme (congestion readings / dashboard / AI)
# Philip Gu (lab submission)

# This script loads a project-themed CSV of corridor reference notes, retrieves rows that
# match a user query across multiple columns, and asks a local Ollama model to produce
# operations-style guidance using only the retrieved context.

# Submission notes (copy for instructor if needed):
# - Data source: CSV of 10 corridor records (location, zone, risk, summary, mitigation)
#   aligned with the City Congestion Tracker Supabase pipeline (locations and zones).
# - Search: tokenize the question, then OR-match each token as a case-insensitive substring
#   across location_name, segment_zone, summary, and mitigation_notes; JSON for the LLM.
# - System prompt: instructs the model to ground answers in retrieved rows, cite locations,
#   and output concise markdown for operators (risks, actions, gaps).

# 0. SETUP ###################################

## 0.1 Load packages ############################

import os
import json
import re

import pandas as pd

## 0.2 Paths ###################################

script_dir = os.path.dirname(os.path.abspath(__file__))
DOCUMENT = os.path.join(script_dir, "data", "city_congestion_reference.csv")

# 1. SEARCH FUNCTION ###########################

# Short stopwords so full-sentence questions still retrieve rows (OR across tokens)
_STOP = frozenset({
    "the", "what", "where", "when", "with", "from", "that", "this", "have", "should",
    "are", "and", "for", "how", "any", "can", "you", "was", "were", "our", "we", "watch",
    "does", "did", "there", "their", "them", "then", "than", "into", "onto", "also",
})


def _query_tokens(text):
    """Lowercase alphanumeric tokens; drop very short tokens and common stopwords."""
    raw = re.findall(r"[A-Za-z0-9]+", (text or "").lower())
    out = []
    for t in raw:
        if t in _STOP:
            continue
        if t.isdigit() and len(t) >= 2:
            out.append(t)
        elif len(t) >= 3:
            out.append(t)
    return out


def search_congestion_reference(query, csv_path):
    """
    Retrieve CSV rows where any token from the query appears in a primary field.

    Tokenizes the question, then OR-matches across location_name, segment_zone,
    summary, and mitigation_notes (case-insensitive, literal substrings). Supports
    both short keywords ("downtown") and longer operator questions.
    """
    df = pd.read_csv(csv_path)
    tokens = _query_tokens(query)
    if not tokens:
        subset = df.iloc[0:0]
    else:
        mask = pd.Series(False, index=df.index)
        cols = ["location_name", "segment_zone", "summary", "mitigation_notes"]
        for tok in tokens:
            piece = pd.Series(False, index=df.index)
            for c in cols:
                piece = piece | df[c].astype(str).str.lower().str.contains(
                    tok, na=False, regex=False
                )
            mask = mask | piece
        subset = df.loc[mask]
    records = subset.to_dict(orient="records")
    return json.dumps(records, indent=2)


if __name__ == "__main__":
    import runpy
    import requests

    os.chdir(script_dir)

    ollama_script_path = os.path.join(script_dir, "01_ollama.py")
    _ = runpy.run_path(ollama_script_path)

    from functions import agent_run

    MODEL = "smollm2:1.7b"
    PORT = 11434
    OLLAMA_HOST = f"http://localhost:{PORT}"

    # 2. TEST SEARCH ###############################

    print("=== Search self-test (query: downtown) ===")
    test_json = search_congestion_reference("downtown", DOCUMENT)
    print(test_json[:600] + ("..." if len(test_json) > 600 else ""))
    print()

    # 3. RAG WORKFLOW ##############################

    role = (
        "You are a transportation operations assistant for a city congestion dashboard. "
        "You receive JSON: an array of corridor reference records from a trusted internal CSV. "
        "Use ONLY that JSON to answer. Name specific locations and zones when relevant. "
        "If the JSON is empty, say no matching corridors were retrieved and suggest broadening the query. "
        "Output markdown with: (1) short situation overview, (2) bullet risks or patterns, "
        "(3) bullet mitigation actions from the data, (4) one line on data gaps if context is thin."
    )

    queries = [
        "What should we watch on Highway 101 and the North Corridor?",
        "Where is pedestrian or curb activity a problem downtown?",
    ]

    for user_topic in queries:
        print(f"=== RAG query: {user_topic!r} ===")
        retrieved = search_congestion_reference(user_topic, DOCUMENT)
        answer = agent_run(role=role, task=retrieved, model=MODEL, output="text")
        print(answer)
        print()

    # 4. ALTERNATIVE: direct chat (sanity check) ###

    CHAT_URL = f"{OLLAMA_HOST}/api/chat"
    messages = [
        {"role": "system", "content": role},
        {"role": "user", "content": search_congestion_reference("bridge", DOCUMENT)},
    ]
    body = {"model": MODEL, "messages": messages, "stream": False}
    response = requests.post(CHAT_URL, json=body)
    response.raise_for_status()
    print("=== Alternative /api/chat (query concept: bridge) ===")
    print(response.json()["message"]["content"])
