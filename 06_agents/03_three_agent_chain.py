#!/usr/bin/env python3

# 03_two_agent_chain.py
# Simple 3-Agent Chained Workflow
# Pairs with 03_agents.py and functions.py
# Tim Fraser

# This script demonstrates a minimal 3‑agent chain.
# Agent 1 takes raw data and produces a short natural‑language summary.
# Agent 2 takes that summary as input and produces a structured markdown report.
# Agent 3 takes the draft report and polishes it for tone, clarity, and brevity.
# Students can use this as a template for building longer multi‑agent workflows.

# 0. SETUP ###################################

## 0.1 Load Packages ############################

import pandas as pd  # for simple tabular data

# Load helper function for running agents
from functions import agent_run


# 1. CREATE RAW DATA ###################################

# For this simple example, we will create a small in‑memory dataset
# instead of calling an external API. In practice, this "raw data"
# could come from a CSV, database, or web service.

data = pd.DataFrame(
    {
        "product": ["Widget A", "Widget B", "Widget C", "Widget D"],
        "region": ["North", "South", "East", "West"],
        "units_sold": [120, 75, 200, 50],
        "return_rate": [0.02, 0.05, 0.01, 0.08],
    }
)


# 2. AGENT 1 – DATA SUMMARY ###################################

# Agent 1's job:
# - Read the raw table
# - Produce a concise plain‑language summary of key trends
# - Keep the output short and easy to pass to the next agent

role_agent1 = (
    "You are a data analyst working with a small sales dataset. "
    "You receive a markdown table of sales data as plain text and "
    "produce a short, clear summary of the main patterns. "
    "Focus on which products and regions are doing well or poorly, "
    "and highlight anything notable about return rates. "
    "Return your answer as exactly 3–5 markdown bullet points, "
    "with no title, no extra commentary, and no explanation of your process."
)

# Convert the DataFrame to a simple text table for the model
task_agent1 = data.to_markdown(index=False)

# Try to call the model. If Ollama is not running or the API
# is unavailable, fall back to a simple hard‑coded summary so
# the script still runs and demonstrates chaining.
try:
    summary_text = agent_run(
        role=role_agent1,
        task=task_agent1,
        model="smollm2:135m",
        output="text",
    )
except Exception:
    summary_text = (
        "- Widget C has the highest sales overall.\n"
        "- Widget D has the lowest sales and the highest return rate.\n"
        "- The South and West regions underperform compared to North and East."
    )


# 3. AGENT 2 – STRUCTURED REPORT ###################################

# Agent 2's job:
# - Take the summary from Agent 1
# - Turn it into a structured markdown report for a manager
# - Demonstrate that the second agent ONLY sees Agent 1's output

role_agent2 = (
    "You are a communications specialist creating a short report for a busy manager. "
    "You receive an analytical summary in bullet points and turn it into "
    "a clear, well‑formatted executive summary. "
    "Use markdown with:\n"
    "1) A level‑1 title line starting with '# ',\n"
    "2) A short introductory paragraph (2–3 sentences), and\n"
    "3) A level‑2 heading '## Key Takeaways' followed by a bullet list. "
    "Do not add any sections other than these. Keep the total length under 250 words."
)

task_agent2 = summary_text

try:
    draft_report = agent_run(
        role=role_agent2,
        task=task_agent2,
        model="smollm2:135m",
        output="text",
    )
except Exception:
    draft_report = (
        "# Executive Summary: Widget Sales Performance\n\n"
        "This short report summarizes recent sales and return performance across four widgets "
        "and regions. It highlights products that are performing strongly, products that may "
        "require attention, and regions where sales are lagging.\n\n"
        "## Key Takeaways\n"
        "- Widget C is currently the strongest performer in total units sold.\n"
        "- Widget D combines low sales volume with a relatively high return rate.\n"
        "- The South and West regions trail the North and East in units sold.\n"
        "- These patterns suggest opportunities to improve quality for Widget D and to "
        "target support to weaker regions."
    )


# 4. AGENT 3 – EDITOR / POLISHING ###################################

# Agent 3's job:
# - Take the draft report from Agent 2
# - Polish the writing for clarity, tone, and brevity
# - Ensure the output is clean markdown that is ready to share

role_agent3 = (
    "You are an editor for executive communications. "
    "You receive a short markdown report and lightly edit it for clarity, "
    "professional tone, and conciseness. "
    "Preserve the existing headings and structure (title, introduction paragraph, "
    "and '## Key Takeaways' section), but you may rephrase sentences and tighten wording. "
    "Return only the final polished markdown report with no additional notes or commentary."
)

task_agent3 = draft_report

try:
    final_report = agent_run(
        role=role_agent3,
        task=task_agent3,
        model="smollm2:135m",
        output="text",
    )
except Exception:
    final_report = draft_report


# 5. VIEW RESULTS ###################################

print("=== RAW DATA (first rows) ===")
print(data.head())
print("\n=== AGENT 1 SUMMARY (input to Agent 2) ===")
print(summary_text)
print("\n=== AGENT 2 DRAFT REPORT (input to Agent 3) ===")
print(draft_report)
print("\n=== AGENT 3 FINAL POLISHED REPORT ===")
print(final_report)
