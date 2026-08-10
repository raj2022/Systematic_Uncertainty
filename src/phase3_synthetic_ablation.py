"""
phase3_synthetic_ablation.py

Phase 3, part A (synthetic half): runs both Phase 1 (keyword) and
Phase 2 (LLM) detectors against the synthetic BASE paragraph and each
of its 5 single-disclosure VARIANTS (see synthetic_ablation_texts.py).

For each variant, checks two things:
1. Did the TARGET element correctly flip from absent (on BASE) to
   disclosed (on the VARIANT)? This is the core test -- does the
   detector respond to the actual content added.
2. Did any OTHER element's prediction change between BASE and the
   VARIANT, despite no change to that element's content? A change here
   is a red flag: it suggests the detector (or at least this specific
   variant's phrasing) is picking up something other than the intended
   signal -- e.g. paragraph length, an incidental word overlap, or
   writing style -- which is exactly the confound this whole phase
   exists to catch.

This complements (does not replace) the real-paper ablation, which
uses actual gold-set text with a disclosure sentence removed/added --
synthetic text is fully controlled but may not reflect how detectors
perform on real, messier prose.

Usage:
    python src/phase3_synthetic_ablation.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from synthetic_ablation_texts import BASE, VARIANTS
from phase1_detector import predict as phase1_predict
from phase2_classifier import call_llm, parse_llm_response, CHECKLIST_COLS
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

RESULTS_DIR = Path("results")


def run_phase1(text: str) -> dict:
    return phase1_predict(text)


def run_phase2(client: anthropic.Anthropic, text: str) -> dict:
    response = call_llm(client, text)
    return parse_llm_response(response)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set -- needed for Phase 2 ablation test.")
    client = anthropic.Anthropic(api_key=api_key)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Scoring BASE paragraph (should be absent on all 5 elements)...")
    base_p1 = run_phase1(BASE)
    base_p2 = run_phase2(client, BASE)

    rows = []
    for target_element, variant_text in VARIANTS.items():
        print(f"Scoring variant: {target_element}...")
        var_p1 = run_phase1(variant_text)
        var_p2 = run_phase2(client, variant_text)

        for element in CHECKLIST_COLS:
            row = {
                "target_element": target_element,
                "checked_element": element,
                "is_target": element == target_element,
                "phase1_base": base_p1[element],
                "phase1_variant": var_p1[element],
                "phase1_changed": base_p1[element] != var_p1[element],
                "phase2_base": base_p2[element],
                "phase2_variant": var_p2[element],
                "phase2_changed": base_p2[element] != var_p2[element],
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    out_path = RESULTS_DIR / "phase3_synthetic_ablation.csv"
    df.to_csv(out_path, index=False)
    print(f"\nWrote full results to {out_path}\n")

    print("=" * 90)
    print("TARGET ELEMENT: did it correctly flip absent -> disclosed?")
    print("=" * 90)
    target_rows = df[df["is_target"]]
    summary = target_rows[[
        "target_element", "phase1_base", "phase1_variant", "phase1_changed",
        "phase2_base", "phase2_variant", "phase2_changed"
    ]]
    print(summary.to_string(index=False))

    print("\n" + "=" * 90)
    print("NON-TARGET ELEMENTS: any spurious changes? (should all be False)")
    print("=" * 90)
    non_target = df[~df["is_target"]]
    spurious_p1 = non_target[non_target["phase1_changed"]]
    spurious_p2 = non_target[non_target["phase2_changed"]]

    if len(spurious_p1) == 0:
        print("Phase 1: no spurious changes on any non-target element. Clean.")
    else:
        print(f"Phase 1: {len(spurious_p1)} spurious change(s):")
        print(spurious_p1[["target_element", "checked_element", "phase1_base", "phase1_variant"]].to_string(index=False))

    if len(spurious_p2) == 0:
        print("\nPhase 2: no spurious changes on any non-target element. Clean.")
    else:
        print(f"\nPhase 2: {len(spurious_p2)} spurious change(s):")
        print(spurious_p2[["target_element", "checked_element", "phase2_base", "phase2_variant"]].to_string(index=False))


if __name__ == "__main__":
    main()
