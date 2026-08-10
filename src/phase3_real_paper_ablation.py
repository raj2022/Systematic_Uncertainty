"""
phase3_real_paper_ablation.py

Phase 3, part A (real-paper half): for each of the five checklist
elements, picks one gold-set paper hand-labeled "disclosed" for that
element, fetches its real full text, automatically locates the
sentence(s) that triggered the Phase 1 regex match, and removes just
those sentence(s) to produce a "redacted" version -- everything else
in the paper is untouched.

Both detectors are then run on the ORIGINAL and REDACTED text. This
tests something the synthetic ablation (phase3_synthetic_ablation.py)
cannot: whether detectors respond correctly to real, messy prose, not
just clean hand-written paragraphs. The synthetic test isolates content
from style; this test checks real-world robustness.

Sentence-boundary splitting is naive (split on '. ') -- this can
occasionally over- or under-redact at abbreviations or decimals, a
known limitation worth checking by eye against the printed redacted
excerpt before trusting the result for any one paper.

Usage:
    python src/phase3_real_paper_ablation.py
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import anthropic
import pandas as pd
from dotenv import load_dotenv

from phase1_detector import CHECKLIST_PATTERNS, fetch_fulltext, predict as phase1_predict
from phase2_classifier import CHECKLIST_COLS, call_llm, parse_llm_response

load_dotenv()

GOLD_PATH = Path("data/gold_set/gold_set_sample.csv")
RESULTS_DIR = Path("results")


def pick_example_paper(df: pd.DataFrame, element: str) -> str | None:
    """First applicable paper hand-labeled 'disclosed' for this element."""
    candidates = df[df[element] == "disclosed"]
    if len(candidates) == 0:
        return None
    return candidates.iloc[0]["arxiv_id"]


def redact_element(text: str, element: str) -> tuple[str, list[str]]:
    """Finds sentences containing any pattern for this element and
    removes them. Returns (redacted_text, removed_sentences)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    patterns = CHECKLIST_PATTERNS[element]

    kept, removed = [], []
    for s in sentences:
        if any(re.search(p, s, flags=re.IGNORECASE) for p in patterns):
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
    df = pd.read_csv(GOLD_PATH, dtype=str).fillna("")

    rows = []
    for element in CHECKLIST_COLS:
        arxiv_id = pick_example_paper(df, element)
        if arxiv_id is None:
            print(f"No disclosed example found for {element}, skipping.")
            continue

        print(f"\n{'=' * 70}\n{element}: using {arxiv_id}\n{'=' * 70}")
        text = fetch_fulltext(arxiv_id)
        if text is None:
            print("  Could not fetch full text, skipping.")
            continue

        redacted, removed = redact_element(text, element)
        if not removed:
            print(f"  WARNING: regex found nothing to redact in {arxiv_id} for {element} "
                  "(gold label may rely on phrasing the regex doesn't catch -- expected, "
                  "given Phase 1's known recall gaps). Skipping this element.")
            continue

        print(f"  Removed {len(removed)} sentence(s):")
        for s in removed:
            print(f"    - {s[:150]}{'...' if len(s) > 150 else ''}")

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

    result_df = pd.DataFrame(rows)
    out_path = RESULTS_DIR / "phase3_real_paper_ablation.csv"
    result_df.to_csv(out_path, index=False)
    print(f"\n\nWrote full results to {out_path}\n")

    if len(result_df) == 0:
        print("No results -- every element was skipped (no example paper or no redactable sentence).")
        return

    print("=" * 90)
    print("TARGET ELEMENT: did removing the disclosing sentence flip disclosed -> absent?")
    print("=" * 90)
    target_rows = result_df[result_df["is_target"]]
    print(target_rows[[
        "target_element", "arxiv_id", "phase1_original", "phase1_redacted", "phase1_changed",
        "phase2_original", "phase2_redacted", "phase2_changed"
    ]].to_string(index=False))

    print("\n" + "=" * 90)
    print("NON-TARGET ELEMENTS: any spurious changes? (should all be False)")
    print("=" * 90)
    non_target = result_df[~result_df["is_target"]]
    spurious_p1 = non_target[non_target["phase1_changed"]]
    spurious_p2 = non_target[non_target["phase2_changed"]]

    if len(spurious_p1) == 0:
        print("Phase 1: no spurious changes. Clean.")
    else:
        print(f"Phase 1: {len(spurious_p1)} spurious change(s):")
        print(spurious_p1[["target_element", "checked_element", "arxiv_id",
                            "phase1_original", "phase1_redacted"]].to_string(index=False))

    if len(spurious_p2) == 0:
        print("\nPhase 2: no spurious changes. Clean.")
    else:
        print(f"\nPhase 2: {len(spurious_p2)} spurious change(s):")
        print(spurious_p2[["target_element", "checked_element", "arxiv_id",
                            "phase2_original", "phase2_redacted"]].to_string(index=False))


if __name__ == "__main__":
    main()
