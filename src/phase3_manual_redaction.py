"""
phase3_manual_redaction.py

Manual-phrase version of the real-paper ablation, for elements where
Phase 1's regex found nothing to redact (walk_forward_validation,
multi_window_validation) -- meaning the automatic version in
phase3_real_paper_ablation.py couldn't test these on real text at all.

Instead of relying on CHECKLIST_PATTERNS, this searches for a specific
phrase drawn directly from the hand-labeler's own note on that paper
(the actual language that justified the "disclosed" label), removes
sentences containing it, and runs both detectors on original vs.
redacted text -- same before/after logic as the automatic version.

Usage:
    python src/phase3_manual_redaction.py
"""

import re
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import anthropic
import pandas as pd
from dotenv import load_dotenv

from phase1_detector import fetch_fulltext, predict as phase1_predict
from phase2_classifier import CHECKLIST_COLS, call_llm, parse_llm_response

load_dotenv()

RESULTS_DIR = Path("results")

# (arxiv_id, target_element, search_phrase) -- phrase drawn from the
# hand-labeler's own note justifying the "disclosed" call on that paper.
CASES = [
    ("2607.25189v1", "walk_forward_validation", "expanding estimation window"),
    ("2508.02686v1", "multi_window_validation", "20 trading days"),
]


def redact_phrase(text: str, phrase: str) -> tuple[str, list[str]]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept, removed = [], []
    for s in sentences:
        if phrase.lower() in s.lower():
            removed.append(s)
        else:
            kept.append(s)
    return " ".join(kept), removed


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set.")
    client = anthropic.Anthropic(api_key=api_key)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for arxiv_id, element, phrase in CASES:
        print(f"\n{'=' * 70}\n{element}: {arxiv_id}, searching for '{phrase}'\n{'=' * 70}")
        text = fetch_fulltext(arxiv_id)
        if text is None:
            print("  Could not fetch full text, skipping.")
            continue

        redacted, removed = redact_phrase(text, phrase)
        if not removed:
            print(f"  WARNING: phrase '{phrase}' not found in fetched text, skipping.")
            continue

        print(f"  Removed {len(removed)} sentence(s):")
        for s in removed:
            print(f"    - {s[:200]}{'...' if len(s) > 200 else ''}")

        orig_p1 = phase1_predict(text)
        red_p1 = phase1_predict(redacted)
        orig_p2 = parse_llm_response(call_llm(client, text))
        red_p2 = parse_llm_response(call_llm(client, redacted))

        for checked_element in CHECKLIST_COLS:
            rows.append({
                "target_element": element,
                "checked_element": checked_element,
                "is_target": checked_element == element,
                "arxiv_id": arxiv_id,
                "phase1_original": orig_p1[checked_element],
                "phase1_redacted": red_p1[checked_element],
                "phase1_changed": orig_p1[checked_element] != red_p1[checked_element],
                "phase2_original": orig_p2[checked_element],
                "phase2_redacted": red_p2[checked_element],
                "phase2_changed": orig_p2[checked_element] != red_p2[checked_element],
            })

    df = pd.DataFrame(rows)
    out_path = RESULTS_DIR / "phase3_manual_redaction.csv"
    df.to_csv(out_path, index=False)
    print(f"\n\nWrote results to {out_path}\n")

    if len(df) == 0:
        print("No results.")
        return

    print("=" * 90)
    print("TARGET ELEMENT: did removing the phrase flip disclosed -> absent?")
    print("=" * 90)
    target_rows = df[df["is_target"]]
    print(target_rows[[
        "target_element", "arxiv_id", "phase1_original", "phase1_redacted", "phase1_changed",
        "phase2_original", "phase2_redacted", "phase2_changed"
    ]].to_string(index=False))

    print("\n" + "=" * 90)
    print("NON-TARGET ELEMENTS: any spurious changes?")
    print("=" * 90)
    non_target = df[~df["is_target"]]
    spurious_p1 = non_target[non_target["phase1_changed"]]
    spurious_p2 = non_target[non_target["phase2_changed"]]
    if len(spurious_p1) == 0:
        print("Phase 1: no spurious changes. Clean.")
    else:
        print(spurious_p1[["target_element", "checked_element", "arxiv_id",
                            "phase1_original", "phase1_redacted"]].to_string(index=False))
    if len(spurious_p2) == 0:
        print("Phase 2: no spurious changes. Clean.")
    else:
        print(spurious_p2[["target_element", "checked_element", "arxiv_id",
                            "phase2_original", "phase2_redacted"]].to_string(index=False))


if __name__ == "__main__":
    main()
