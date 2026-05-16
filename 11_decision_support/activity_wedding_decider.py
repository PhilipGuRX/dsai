#!/usr/bin/env python3
# activity_wedding_decider.py
# AI Decider: Wedding Venue Comparison with local Ollama
# Pairs with 11_decision_support activity instructions
# Tim Fraser
#
# This script sends two prompt variants to a local Ollama model.
# It helps students compare how recommendations change when priorities shift.

# 0. Setup #################################

## 0.1 Load Packages ############################

import json
import os
from pathlib import Path

import requests


## 0.2 Constants ################################

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = os.getenv("OLLAMA_MODEL", "smollm2:1.7b")
# Large prompts + 16-row tables need a generous ceiling; override with OLLAMA_TIMEOUT if needed.
OLLAMA_TIMEOUT_S = int(os.getenv("OLLAMA_TIMEOUT", "600"))
# Cap completion length so runs finish; raise if the model truncates the table.
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))

SYSTEM_PROMPT = """You are a structured data extractor and decision analyst.
Your job is to extract key attributes from unstructured venue descriptions,
build a comparison table, and recommend the top 3 venues based on the client's priorities.

Always return:
1. A markdown table with columns: Venue, Capacity, Approx. Price/Night, Catering, Outdoor, Parking, Vibe (1 word)
2. A ranked shortlist of top 3 venues with 1-sentence justification each
3. One sentence noting any venues you had to exclude due to missing information

Be concise. Do not invent data that is not in the descriptions.
"""

VENUE_DATA = """Venue 1 — The Rosewood Estate
A sprawling property in the Hudson Valley with manicured gardens and a restored barn.
Capacity up to 175 guests. Rental fee is $17,500 Friday–Sunday. They have a preferred
catering list with 4 approved vendors. Outdoor ceremony space available with a rain
backup tent. Parking for ~80 cars on site.

Venue 2 — The Grand Metropolitan Hotel
Downtown ballroom, seats up to 300. In-house catering only. Pricing starts at $12,000
for the ballroom rental, catering packages extra. Valet parking. No outdoor space.

Venue 3 — Lakeview Pavilion
Outdoor lakeside pavilion. No indoor backup. BYOB catering. Fits about 90 people
comfortably, 110 at a squeeze. Very affordable — around $2,500 for a weekend.

Venue 4 — Thornfield Manor
Historic manor house, 8 acres. Exclusive use for the weekend. Price: $18,000.
In-house catering team. Ceremony can be held on the grounds or in the chapel.
Capacity 150. Featured in several bridal magazines.

Venue 5 — The Foundry at Millworks
Industrial-chic converted factory. Very trendy. Capacity 250. Bring your own vendors.
Rental is $5,000. Rooftop available for cocktail hour. No on-site parking — street
parking and nearby garage only.

Venue 6 — Sunrise Farm & Vineyard
Working vineyard with barn and outdoor ceremony terrace. Stunning views. Capacity 130.
Weekend rental $9,800. Catering through their in-house team or 2 approved vendors.
Ample parking. Very popular — books 18 months out.

Venue 7 — The Atrium Club
Corporate event space that does weddings on weekends. Very flexible on catering.
Fits 300+. Located downtown. Pricing on request — sales team says "typically $9,000–$14,000
depending on date." Not particularly romantic but very professional.

Venue 8 — Cedar Hollow Retreat
Rustic woodland lodge. Intimate and cozy. Max 60 guests. $3,200 for a Saturday.
Outside catering allowed. No formal parking lot — guests park in a field.

Venue 9 — The Belvedere
Upscale rooftop venue with skyline views. Indoor/outdoor setup. Capacity 180.
In-house catering required. Rental + minimum catering spend is $28,000.
Very elegant. Valet only.

Venue 10 — Harborside Event Center
Waterfront venue, brand new. Capacity 220. Pricing TBD — still finalizing packages.
Flexible on catering. Outdoor terrace available. Large parking lot.

Venue 11 — The Ivy House
Garden venue in a residential neighborhood. Permits outdoor ceremonies.
Capacity 100. $4,500 rental. BYOB catering. Street parking only — coordinator
recommends a shuttle from a nearby lot.

Venue 12 — Maple Ridge Country Club
Classic country club setting. Capacity 160. In-house catering only, known for
being very good. Rental from $28,500. Golf course backdrop for photos.
Ample parking. Private feel.

Venue 13 — The Glasshouse Conservatory
All-glass event space surrounded by botanical gardens. Very dramatic.
Capacity 140. $18,000 rental, catering open. Outdoor garden available for ceremonies.
Parking on site. Popular for spring weddings.

Venue 14 — Millbrook Inn
Country inn with event lawn. Venue rental $10,500. Capacity 120. Outside catering
allowed. Some overnight rooms available for wedding party. Very charming.

Venue 15 — The Warehouse District Loft
Raw, urban space. Very minimal. No catering kitchen. Capacity 200.
$8,800 rental. Not ideal for traditional weddings.

Venue 16 — Cloverfield Farms
Family-owned working farm. Barn + outdoor space. Capacity 135.
$6,000 Friday–Sunday. Preferred caterer list (3 vendors).
Casual, warm atmosphere. Lots of parking. Dogs welcome.
"""

PRIORITIES_STAGE_1 = """Here are the couple's priorities:
- Budget: under $8,000 for venue rental
- Guest count: ~120 people
- Vibe: romantic, not too corporate
- Must have outdoor ceremony option
- Catering must be in-house or on an approved vendor list

Here are descriptions of 16 venues. Please analyze and recommend.
"""

PRIORITIES_STAGE_2 = """Here are the couple's priorities:
- Budget: flexible, up to $15,000
- Guest count: ~200 people
- Vibe: elegant, grand
- Outdoor is a nice-to-have but not required
- No catering constraint

Here are descriptions of 16 venues. Please analyze and recommend.
"""


# 1. Helper Functions ############################

def run_ollama_chat(system_prompt: str, user_prompt: str) -> str:
    """Send one chat request to local Ollama and return model text."""
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "options": {"num_predict": OLLAMA_NUM_PREDICT},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT_S)
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


def save_markdown(path: Path, title: str, content: str) -> None:
    """Save stage output to markdown for easy screenshot capture."""
    body = f"# {title}\n\n{content.strip()}\n"
    path.write_text(body, encoding="utf-8")


# 2. Run Activity #################################

def main() -> None:
    # Keep outputs near this script for easy submission artifacts.
    output_dir = Path(__file__).resolve().parent / "activity_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    stage_1_prompt = f"{PRIORITIES_STAGE_1}\n\n{VENUE_DATA}"
    stage_2_prompt = f"{PRIORITIES_STAGE_2}\n\n{VENUE_DATA}"

    print(f"Model: {MODEL_NAME} (timeout {OLLAMA_TIMEOUT_S}s)")
    print("Stage 1: calling Ollama…")
    stage_1_result = run_ollama_chat(SYSTEM_PROMPT, stage_1_prompt)
    save_markdown(output_dir / "stage1_wedding_decider.md", "Stage 1 Output", stage_1_result)
    print("Stage 1: saved.")

    print("Stage 2: calling Ollama…")
    stage_2_result = run_ollama_chat(SYSTEM_PROMPT, stage_2_prompt)
    save_markdown(output_dir / "stage2_wedding_decider.md", "Stage 2 Output", stage_2_result)
    print("Stage 2: saved.")

    print("Saved outputs:")
    print(f"- {output_dir / 'stage1_wedding_decider.md'}")
    print(f"- {output_dir / 'stage2_wedding_decider.md'}")

    # Save a lightweight JSON snapshot in case students want structured archiving.
    structured_path = output_dir / "stage_outputs.json"
    structured_payload = {
        "model": MODEL_NAME,
        "stage_1": stage_1_result,
        "stage_2": stage_2_result,
    }
    structured_path.write_text(json.dumps(structured_payload, indent=2), encoding="utf-8")
    print(f"- {structured_path}")


if __name__ == "__main__":
    main()
