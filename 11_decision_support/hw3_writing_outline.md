# Writing component outline (draft in your own words for .docx)

> **Important:** The homework requires ~500 words written by **you**, not by AI. Use this outline only; rewrite every paragraph in your voice before submitting.

## Paragraph 1 — Purpose and design

- What problem does the system solve? (QA for AI wedding venue decision reports.)
- Who is the “user”? (You / a planner reviewing model output before sending to a client.)
- High-level flow: generate reports → AI reviewer scores rubric → composite → statistics.

## Paragraph 2 — Custom validator (not LAB Likert)

- List your dimensions (priority alignment, table coverage, etc.).
- Explain why counts and 0–100 scales fit structured decision reports better than generic formality/clarity Likert items.
- Mention benchmarks (e.g., 16/16 venues, exclusion note required).

## Paragraph 3 — Experimental design

- Prompts A (minimal), B (structured), C (checklist).
- Sample size: ___ reports per prompt, ___ total scores.
- Same venue data and Stage 1 priorities for all conditions.

## Paragraph 4 — Statistical results

- Paste from `hw3_outputs/statistical_summary.txt`:
  - Means for A, B, C
  - ANOVA: F = ___, p = ___
  - T-test (top two): T = ___, p = ___
- State which prompt won and whether differences are significant at α = 0.05.

## Paragraph 5 — Design choices and challenges

- Examples: JSON parsing failures, small model truncating tables, validator variance, runtime.
- What you would change next (more runs, human spot-check, different model).
