# lab_two_agent_congestion_tools.py
# LAB: Two-agent workflow with a custom tool (City Congestion reference CSV)
# Pairs with LAB_multi_agent_with_tools.md and 07_rag/lab_city_congestion_rag.py
# Philip Gu

# Task 1: Custom tool — query_corridor_reference — wraps the same retrieval logic as
# the custom RAG lab (token OR-search over corridor CSV rows). Returns JSON text.
# Task 2: Agent 1 must call the tool; Agent 2 turns the retrieved JSON into an ops briefing.
# Task 3: Run with Ollama up (see 01_ollama.py). If the model skips the tool, tighten role1.

# 0. SETUP ###################################

## 0.1 Load packages ############################

import importlib.util
import os

## 0.2 Import congestion search from 07 RAG lab (without shadowing 08 functions.py) ################

_script_dir = os.path.dirname(os.path.abspath(__file__))
_07_rag_dir = os.path.normpath(os.path.join(_script_dir, "..", "07_rag"))
_lab_rag_path = os.path.join(_07_rag_dir, "lab_city_congestion_rag.py")
_spec = importlib.util.spec_from_file_location("lab_city_congestion_rag", _lab_rag_path)
_lab_rag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lab_rag)
search_congestion_reference = _lab_rag.search_congestion_reference

_CSV_PATH = os.path.join(_07_rag_dir, "data", "city_congestion_reference.csv")

## 0.3 Load agent helpers from this folder ############################

from functions import agent_run

MODEL = "smollm2:1.7b"

# 1. CUSTOM TOOL FUNCTION ###################################

# The LLM calls this by name; keep the implementation deterministic and fast.


def query_corridor_reference(user_query):
    """
    Search the City Congestion Tracker corridor reference CSV for rows relevant
    to an operator question.

    Tokenizes the question, then OR-matches tokens across location_name,
    segment_zone, summary, and mitigation_notes (case-insensitive substrings).
    Returns a JSON array string (pretty-printed) of matching records; "[]" if none.

    Parameters
    ----------
    user_query : str
        Natural-language question or keywords (e.g. "downtown hub", "bridge east").

    Returns
    -------
    str
        JSON text of matching rows for downstream agents.
    """
    q = (user_query or "").strip()
    return search_congestion_reference(q, _CSV_PATH)


# 2. TOOL METADATA ###################################

tool_query_corridor_reference = {
    "type": "function",
    "function": {
        "name": "query_corridor_reference",
        "description": (
            "Search the internal city congestion corridor reference table. "
            "Pass the operator's question or keywords; returns JSON records with "
            "location_name, segment_zone, congestion_risk, summary, and mitigation_notes."
        ),
        "parameters": {
            "type": "object",
            "required": ["user_query"],
            "properties": {
                "user_query": {
                    "type": "string",
                    "description": (
                        "Operator question or search terms to match against corridor fields "
                        "(e.g. 'Highway 101 North', 'downtown station', 'freight corridor')."
                    ),
                }
            },
        },
    },
}

# 3. TWO-AGENT WORKFLOW ###################################

# Agent 1: uses the tool exactly once to fetch JSON context
role_agent1 = (
    "You are a data retrieval assistant for a congestion operations center. "
    "You MUST call the function query_corridor_reference to fetch corridor records. "
    "Pass user_query as a short phrase with the main locations, zones, or risks from "
    "the operator message. Do not invent data; retrieval happens only through the tool."
)

# Simpler user task so small models reliably trigger the tool: single clear ask
task_agent1 = (
    "Operator question: What should we know about downtown corridors and the central "
    "station hub for mitigations and risk? "
    "Call query_corridor_reference with user_query that includes the main place names."
)

result1_calls = agent_run(
    role=role_agent1,
    task=task_agent1,
    model=MODEL,
    output="tools",
    tools=[tool_query_corridor_reference],
)

# Extract tool JSON for Agent 2 (prefer first tool call output)
result1_text = ""
if isinstance(result1_calls, list) and len(result1_calls) > 0:
    out = result1_calls[0].get("output")
    if out is not None:
        result1_text = out if isinstance(out, str) else str(out)

# If the model did not call the tool, run retrieval directly so the demo still completes
if not result1_text or result1_text.strip() == "":
    result1_text = query_corridor_reference("downtown Central Station hub")
    print("Note: Agent 1 did not return tool output; using direct query_corridor_reference fallback.")
    print()

# Agent 2: report from retrieved JSON only
role_agent2 = (
    "You are a senior transportation operations analyst. You receive JSON: an array of "
    "corridor records from a trusted internal reference. Use ONLY that JSON. "
    "Write a concise markdown briefing with: (1) Situation overview, (2) Key risks by "
    "location/zone, (3) Recommended mitigations from the data, (4) One line on gaps if "
    "the JSON is empty or thin. Cite location names from the data."
)

result2 = agent_run(
    role=role_agent2,
    task=result1_text,
    model=MODEL,
    output="text",
    tools=None,
)

# 4. VIEW RESULTS ###################################

print("=== Agent 1 (tool path) ===")
print(result1_calls)
print()

print("=== Context passed to Agent 2 (first 1200 chars) ===")
print(result1_text[:1200] + ("..." if len(result1_text) > 1200 else ""))
print()

print("=== Agent 2 (briefing) ===")
print(result2)
