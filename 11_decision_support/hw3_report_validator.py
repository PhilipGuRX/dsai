#!/usr/bin/env python3
# hw3_report_validator.py
# Homework 3: AI Report Validation System (Wedding Venue Reports)
# Pairs with 11_decision_support/HOMEWORK3.md and hw3_validation_rubric.md
# Tim Fraser
#
# Validates AI-generated wedding venue reports with a custom rubric, runs a
# multi-prompt experiment, and performs statistical comparison (t-test / ANOVA).

# 0. Setup #################################

## 0.1 Load Packages ############################

import argparse
import importlib.util
import json
import os
import re
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
from scipy.stats import bartlett, f_oneway, ttest_ind

# Optional: pip install pingouin (same as 09_text_analysis/03_statistical_comparison.py)
try:
    import pingouin as pg
except ImportError:
    pg = None

## 0.2 Paths and configuration ##################

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "hw3_outputs"
REPORTS_DIR = OUTPUT_DIR / "generated_reports"
RUBRIC_PATH = SCRIPT_DIR / "hw3_validation_rubric.md"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "smollm2:1.7b")
OLLAMA_TIMEOUT_S = int(os.getenv("OLLAMA_TIMEOUT", "300"))
REPORTS_PER_PROMPT = int(os.getenv("HW3_REPORTS_PER_PROMPT", "6"))

# Ground-truth venue text (imported from activity_wedding_decider.py)
_wedding_spec = importlib.util.spec_from_file_location(
    "activity_wedding_decider",
    SCRIPT_DIR / "activity_wedding_decider.py",
)
_wedding = importlib.util.module_from_spec(_wedding_spec)
_wedding_spec.loader.exec_module(_wedding)
VENUE_DATA = _wedding.VENUE_DATA
PRIORITIES = _wedding.PRIORITIES_STAGE_1
USER_TASK = f"{PRIORITIES}\n\n{VENUE_DATA}"

# Three report-generation prompts (experiment factors)
PROMPT_VARIANTS = {
    "A": {
        "label": "Minimal",
        "system": (
            "You are a helpful assistant. Summarize the venues and recommend "
            "three that fit the couple's priorities. Be brief."
        ),
        "temperature": 0.8,
    },
    "B": {
        "label": "Structured",
        "system": """You are a structured data extractor and decision analyst.
Your job is to extract key attributes from unstructured venue descriptions,
build a comparison table, and recommend the top 3 venues based on the client's priorities.

Always return:
1. A markdown table with columns: Venue, Capacity, Approx. Price/Night, Catering, Outdoor, Parking, Vibe (1 word)
2. A ranked shortlist of top 3 venues with 1-sentence justification each
3. One sentence noting any venues you had to exclude due to missing information

Be concise. Do not invent data that is not in the descriptions.
""",
        "temperature": 0.7,
    },
    "C": {
        "label": "Checklist",
        "system": """You are a wedding venue decision analyst. Follow this checklist exactly:
1. Build a markdown table listing ALL 16 venues with columns: Venue, Capacity, Approx. Price/Night, Catering, Outdoor, Parking, Vibe.
2. Rank the top 3 venues; for each, cite which priorities it satisfies (budget ≤ $8k rental, ~120 guests, romantic vibe, outdoor ceremony, in-house or approved catering).
3. End with one sentence excluding any venue you cannot score due to missing price or capacity.
Rules: Use only facts from the descriptions. Flag TBD pricing. Do not recommend venues clearly over budget without noting the conflict.
""",
        "temperature": 0.6,
    },
}

COMPOSITE_WEIGHTS = {
    "priority_alignment": 0.35,
    "source_fidelity": 0.25,
    "table_coverage": 0.20,
    "structure_compliance": 0.10,
    "exclusion_quality": 0.10,
}


# 1. Helper functions ############################

def log_banner(title: str) -> None:
    print(f"\n{'=' * 60}\n📋 {title}\n{'=' * 60}")


def log_step(msg: str) -> None:
    print(f"   ✅ {msg}")


def composite_score(row: dict) -> float:
    """Weighted 0–100 composite from rubric dimensions."""
    table_norm = (float(row["table_coverage"]) / 16.0) * 100.0
    structure_norm = (float(row["structure_compliance"]) / 3.0) * 100.0
    exclusion_norm = float(row["exclusion_quality"]) * 100.0
    score = (
        COMPOSITE_WEIGHTS["priority_alignment"] * float(row["priority_alignment"])
        + COMPOSITE_WEIGHTS["source_fidelity"] * float(row["source_fidelity"])
        + COMPOSITE_WEIGHTS["table_coverage"] * table_norm
        + COMPOSITE_WEIGHTS["structure_compliance"] * structure_norm
        + COMPOSITE_WEIGHTS["exclusion_quality"] * exclusion_norm
    )
    return round(score, 2)


def ollama_chat(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.3,
    json_mode: bool = False,
) -> str:
    """Send one chat request to local Ollama."""
    body = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if json_mode:
        body["format"] = "json"
    response = requests.post(OLLAMA_URL, json=body, timeout=OLLAMA_TIMEOUT_S)
    response.raise_for_status()
    return response.json()["message"]["content"]


def extract_json(text: str) -> dict:
    """Parse JSON from model output (handles fenced or embedded JSON)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


def create_validation_prompt(report_text: str) -> str:
    """Build qualitative content-analysis prompt for the AI reviewer."""
    return f"""You are a qualitative content analyst validating wedding venue decision reports.

Client priorities:
{PRIORITIES}

Source venue descriptions (ground truth):
{VENUE_DATA}

Report to validate:
---
{report_text}
---

Score the report using this rubric. Return ONLY valid JSON:
{{
  "priority_alignment": <0-100, how well top-3 match stated priorities>,
  "table_coverage": <integer 0-16, count distinct venues named in the comparison table>,
  "source_fidelity": <0-100, numeric and venue facts traceable to source>,
  "structure_compliance": <integer 0-3: 1 if markdown table present, +1 if top-3 shortlist, +1 if exclusion note>,
  "exclusion_quality": <0 or 1, 1 if a specific venue and reason are named>,
  "evidence": "<40 words citing strengths or failures>"
}}
"""


def validate_report(report_text: str) -> dict:
    """Run AI reviewer; return parsed scores and composite."""
    raw = ollama_chat(
        "You are a validation reviewer. Respond with valid JSON only.",
        create_validation_prompt(report_text),
        temperature=0.2,
        json_mode=True,
    )
    data = extract_json(raw)
    for key in [
        "priority_alignment",
        "table_coverage",
        "source_fidelity",
        "structure_compliance",
        "exclusion_quality",
    ]:
        if key not in data:
            raise KeyError(f"Missing key in validation JSON: {key}")
    data["composite_score"] = composite_score(data)
    data["evidence"] = data.get("evidence", "")
    return data


def report_path_for(prompt_id: str, run_id: int) -> Path:
    return REPORTS_DIR / f"prompt_{prompt_id}_run_{run_id:02d}.md"


def generate_report(prompt_id: str, run_id: int) -> str:
    """Generate one report using a prompt variant."""
    variant = PROMPT_VARIANTS[prompt_id]
    return ollama_chat(variant["system"], USER_TASK, temperature=variant["temperature"])


def save_report(prompt_id: str, run_id: int, text: str) -> Path:
    path = report_path_for(prompt_id, run_id)
    path.write_text(f"# Report — Prompt {prompt_id}, run {run_id}\n\n{text.strip()}\n", encoding="utf-8")
    return path


# 2. Experiment pipeline ############################


def run_experiment(reports_per_prompt: int = REPORTS_PER_PROMPT, *, resume: bool = True) -> pd.DataFrame:
    """Generate reports for prompts A/B/C and validate each."""
    log_banner("Homework 3 — Prompt experiment")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    scores_path = OUTPUT_DIR / "validation_scores.csv"
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   Reports per prompt: {reports_per_prompt}")
    if resume:
        print("   Resume: skip existing report files when present")

    rows = []
    for prompt_id in ["A", "B", "C"]:
        label = PROMPT_VARIANTS[prompt_id]["label"]
        print(f"\n---- Prompt {prompt_id} ({label}) ----")
        for run_id in range(1, reports_per_prompt + 1):
            path = report_path_for(prompt_id, run_id)
            if resume and path.exists():
                report_text = path.read_text(encoding="utf-8")
                # Strip markdown title line added by save_report
                report_text = re.sub(r"^# Report.*?\n\n", "", report_text, count=1, flags=re.DOTALL)
                log_step(f"Reuse existing report → {path.name}")
            else:
                print(f"   ☁️  Generate {prompt_id} run {run_id}/{reports_per_prompt}…")
                report_text = generate_report(prompt_id, run_id)
                save_report(prompt_id, run_id, report_text)
                log_step(f"Saved report → {path.name} ({len(report_text)} chars)")

            print(f"   ☁️  Validate {prompt_id} run {run_id}…")
            scores = validate_report(report_text)
            row = {
                "prompt_id": prompt_id,
                "prompt_label": label,
                "run_id": run_id,
                "report_path": str(path.relative_to(SCRIPT_DIR)),
                **scores,
            }
            rows.append(row)
            log_step(f"Composite = {scores['composite_score']}")
            pd.DataFrame(rows).to_csv(scores_path, index=False)
            time.sleep(0.5)

    df = pd.DataFrame(rows)
    df.to_csv(scores_path, index=False)
    log_step(f"Wrote {len(df)} rows → {scores_path}")
    return df


# 3. Statistical analysis ############################

def run_statistics(scores: pd.DataFrame) -> dict:
    """Descriptive stats, Bartlett, t-test (best vs runner-up), one-way ANOVA."""
    log_banner("Statistical analysis")
    stats_path = OUTPUT_DIR / "statistical_summary.txt"
    lines = []

    summary = scores.groupby("prompt_id")["composite_score"].agg(["count", "mean", "std"]).round(2)
    print("\n📊 Composite score by prompt:")
    print(summary)
    lines.append("Composite score by prompt:\n" + summary.to_string() + "\n")

    groups = {p: scores.query("prompt_id == @p")["composite_score"].values for p in ["A", "B", "C"]}
    a, b, c = groups["A"], groups["B"], groups["C"]

    b_stat, b_p = bartlett(a, b, c)
    var_equal = b_p >= 0.05
    lines.append(f"\nBartlett test: stat={b_stat:.4f}, p={b_p:.4f}, equal_var={var_equal}\n")
    print(f"\n🔍 Bartlett: stat={b_stat:.4f}, p={b_p:.4f}")

    means = {p: scores.query("prompt_id == @p")["composite_score"].mean() for p in ["A", "B", "C"]}
    best = max(means, key=means.get)
    second = sorted(means, key=means.get, reverse=True)[1]
    print(f"\n📊 Means: A={means['A']:.2f}, B={means['B']:.2f}, C={means['C']:.2f}")
    print(f"   Top prompt: {best} ({means[best]:.2f})")

    # Welch or equal-variance t-test between top two prompts
    x = groups[best]
    y = groups[second]
    if pg is not None:
        tt = pg.ttest(x, y, correction=not var_equal)
        t_p = float(tt["p-val"].values[0] if "p-val" in tt.columns else tt["p_val"].values[0])
        t_stat = float(tt["T"].values[0])
    else:
        t_stat, t_p = ttest_ind(x, y, equal_var=var_equal)
    lines.append(f"\nT-test ({best} vs {second}): T={t_stat:.4f}, p={t_p:.4f}\n")
    print(f"\n📋 T-test {best} vs {second}: T={t_stat:.4f}, p={t_p:.4f}")

    f_stat, f_p = f_oneway(a, b, c)
    if pg is not None:
        if var_equal:
            anova = pg.anova(dv="composite_score", between="prompt_id", data=scores)
        else:
            anova = pg.welch_anova(dv="composite_score", between="prompt_id", data=scores)
        f_stat = float(anova["F"].values[0])
        f_p = float(anova["p-unc"].values[0] if "p-unc" in anova.columns else anova["p_unc"].values[0])
    lines.append(f"One-way ANOVA: F={f_stat:.4f}, p={f_p:.4f}\n")
    print(f"\n📋 One-way ANOVA: F={f_stat:.4f}, p={f_p:.4f}")

    if f_p < 0.05:
        print(f"   ✅ At least one prompt differs significantly (α=0.05). Best: Prompt {best}.")
    else:
        print("   ❌ No significant difference across prompts at α=0.05.")

    stats_path.write_text("\n".join(lines), encoding="utf-8")
    log_step(f"Summary → {stats_path}")
    plot_score_comparison(scores)
    return {
        "means": means,
        "best_prompt": best,
        "t_stat": t_stat,
        "t_p": t_p,
        "f_stat": f_stat,
        "f_p": f_p,
        "bartlett_p": b_p,
    }


def plot_score_comparison(scores: pd.DataFrame) -> None:
    """Save boxplot and bar chart for screenshots."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    order = ["A", "B", "C"]
    data = [scores.query("prompt_id == @p")["composite_score"] for p in order]
    axes[0].boxplot(data, labels=order)
    axes[0].set_ylabel("Composite score (0–100)")
    axes[0].set_title("Validation scores by prompt")
    means = scores.groupby("prompt_id")["composite_score"].mean().reindex(order)
    axes[1].bar(order, means.values, color=["#6baed6", "#74c476", "#fd8d3c"])
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Mean composite score")
    axes[1].set_title("Mean score by prompt")
    fig.tight_layout()
    plot_path = OUTPUT_DIR / "prompt_score_comparison.png"
    fig.savefig(plot_path, dpi=120)
    plt.close(fig)
    log_step(f"Plot → {plot_path}")


def validate_single_report(path: Path) -> None:
    """Validate one markdown report file (for demos / spot checks)."""
    log_banner(f"Validate single report: {path.name}")
    text = path.read_text(encoding="utf-8")
    scores = validate_report(text)
    print(json.dumps(scores, indent=2))
    out = OUTPUT_DIR / f"validation_{path.stem}.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2), encoding="utf-8")
    log_step(f"Wrote → {out}")


# 4. CLI #################################

def main() -> None:
    parser = argparse.ArgumentParser(description="Homework 3 wedding report validation system")
    parser.add_argument(
        "--step",
        choices=["experiment", "stats", "validate"],
        default="experiment",
        help="experiment=generate+validate+stats; stats=CSV only; validate=one file",
    )
    parser.add_argument("--report", type=Path, help="Path to .md report for --step validate")
    parser.add_argument("--reports-per-prompt", type=int, default=REPORTS_PER_PROMPT)
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Regenerate all reports even if files already exist",
    )
    parser.add_argument(
        "--scores-csv",
        type=Path,
        default=OUTPUT_DIR / "validation_scores.csv",
        help="Scores file for --step stats",
    )
    args = parser.parse_args()

    if args.step == "validate":
        if not args.report:
            default = SCRIPT_DIR / "activity_outputs" / "stage1_wedding_decider.md"
            args.report = default
        validate_single_report(args.report.resolve())
        return

    if args.step == "experiment":
        scores = run_experiment(args.reports_per_prompt, resume=not args.no_resume)
        run_statistics(scores)
        return

    if args.step == "stats":
        if not args.scores_csv.exists():
            raise FileNotFoundError(f"Scores CSV not found: {args.scores_csv}. Run --step experiment first.")
        scores = pd.read_csv(args.scores_csv)
        print(f"   ✅ Loaded {len(scores)} validation rows from {args.scores_csv}")
        run_statistics(scores)


if __name__ == "__main__":
    main()
