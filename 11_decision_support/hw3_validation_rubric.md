# Homework 3: Wedding Report Validation Rubric

Custom qualitative content-analysis criteria for **AI-generated wedding venue decision reports**. These dimensions are tailored to structured decision-support output (comparison table, top-3 shortlist, exclusion note) and client priorities—not the generic 1–5 Likert scales used in [`LAB_ai_quality_control.md`](../09_text_analysis/LAB_ai_quality_control.md).

## Validation criteria

| Dimension | Description | Scale / method | Benchmark |
|-----------|-------------|----------------|-----------|
| **Priority alignment** | Do the top-3 recommended venues match the couple’s stated budget, guest count, vibe, outdoor need, and catering rules? | **0–100** (percent of priority checks passed across the shortlist) | **≥ 75** — at least ~3 of 4 priority themes satisfied on average across top 3 |
| **Table coverage** | How many of the 16 source venues appear in the comparison table? | **0–16** venues counted → normalized to 0–100 | **16/16** (100%) — full venue inventory represented |
| **Source fidelity** | Are capacity and price figures traceable to the source descriptions (no invented venues or wild numeric drift)? | **0–100** (AI reviewer estimates fidelity from spot-checks) | **≥ 85** — at most minor rounding or labeling differences |
| **Structure compliance** | Required report sections present? | **0–3** checklist: (1) markdown table, (2) ranked top 3, (3) exclusion note | **3/3** — all sections present and labeled |
| **Exclusion quality** | Is the exclusion note specific (names a venue and a concrete reason)? | **0 or 1** (binary) | **1** — cites a venue and a defensible reason (e.g., missing price, under capacity) |
| **Composite score** | Weighted summary for experiment analysis | **0–100** | **≥ 70** acceptable; **≥ 80** strong |

### Composite weights

| Dimension | Weight |
|-----------|--------|
| Priority alignment | 35% |
| Source fidelity | 25% |
| Table coverage (normalized) | 20% |
| Structure compliance (normalized) | 10% |
| Exclusion quality (×100) | 10% |

## How this differs from the LAB

| LAB (`02_ai_quality_control`) | This homework rubric |
|------------------------------|----------------------|
| Generic writing quality (formality, succinctness, clarity) on 1–5 Likert | Domain-specific **decision quality** (priorities, table coverage, exclusions) |
| Boolean “accurate” vs. source table | **Priority alignment** scored against explicit couple constraints |
| Same 1–5 scale for all subjective traits | Mix of **counts (0–16)**, **binary**, and **0–100** scales |
| No required report structure | **Structure compliance** checklist for decision-report format |

## AI reviewer role

The validator model receives:

1. The **client priorities** used to generate the report  
2. The **source venue descriptions** (ground truth)  
3. The **report text** to evaluate  

It returns **JSON only** with numeric scores, checklist fields, a short evidence string, and a computed-ready `composite_score` (recomputed in code for consistency).
