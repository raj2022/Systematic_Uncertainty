"""
phase4_corpus_scale.py

Phase 4 (stretch): applies the validated applicability screen and the
Phase 2 checklist classifier across the FULL raw corpus (all papers
pulled by pull_arxiv.py, not just the 50-paper gold set), and reports
an honestly bounded, precision-and-recall-qualified estimate of how
common each disclosure gap is -- explicitly NOT a headline "X% of
papers are wrong" claim, per the proposal's Section 6 non-goal.

Two-step pipeline per paper:
1. Applicability screen (validated against the 50-paper gold set at
   accuracy=0.90, precision=0.938, recall=0.909 -- see notes/008).
   Papers judged not_applicable are excluded from checklist scoring.
2. For applicable papers, the same five-element checklist prompt used
   in Phase 2 (validated against gold labels in notes/006).

Every reported percentage in the final summary is qualified with the
relevant precision/recall from validation, not presented as a bare
population estimate.

This is expensive: ~500 papers x up to 2 API calls each. Runs in
resumable batches and writes progress incrementally so a partial run
is not lost.

Usage:
    python src/phase4_corpus_scale.py [--limit N] [--start-from ARXIV_ID]
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import anthropic
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from phase1_detector import fetch_fulltext
from phase2_classifier import CHECKLIST_COLS, EXTRACTION_PROMPT, MODEL, parse_llm_response
from phase4_applicability_validation import APPLICABILITY_PROMPT, parse_applicability

load_dotenv()

RAW_PATH = Path("data/raw/qfin_st_metadata.csv")
RESULTS_DIR = Path("results")
OUT_PATH = RESULTS_DIR / "phase4_corpus_scale_predictions.csv"

# Validated performance of the applicability screen against the 50-paper
# gold set (notes/008) -- used to qualify the final estimate, not to
# adjust predictions.
APPLICABILITY_VALIDATION = {"accuracy": 0.90, "precision": 0.938, "recall": 0.909}

# Validated Phase 2 checklist performance against the 33 applicable
# gold-set papers (notes/006) -- same purpose.
CHECKLIST_VALIDATION = {
    "walk_forward_validation": {"precision": 1.000, "recall": 0.846},
    "purged_embargoed_cv": {"precision": None, "recall": None},  # n=1, unscoreable
    "out_of_sample_cost_modeling": {"precision": 1.000, "recall": 0.750},
    "multiple_testing_correction": {"precision": 1.000, "recall": 1.000},
    "multi_window_validation": {"precision": 0.833, "recall": 0.455},
}


def call_llm(client: anthropic.Anthropic, prompt_template: str, text: str,
             max_tokens: int, max_chars: int = 60000, max_retries: int = 3) -> str:
    truncated = text[:max_chars]
    prompt = prompt_template.format(paper_text=truncated)
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in response.content if hasattr(b, "text"))
        except anthropic.RateLimitError:
            wait = 15 * (attempt + 1)
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
    raise RuntimeError("Still rate-limited after retries")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                         help="Only process the first N papers (for testing before a full run)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set.")
    client = anthropic.Anthropic(api_key=api_key)

    if not RAW_PATH.exists():
        raise SystemExit(f"{RAW_PATH} not found -- run pull_arxiv.py first.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW_PATH, dtype=str).fillna("")
    if args.limit:
        df = df.head(args.limit)

    # Resume support: skip arxiv_ids already in the output file.
    done_ids = set()
    if OUT_PATH.exists():
        existing = pd.read_csv(OUT_PATH, dtype=str)
        done_ids = set(existing["arxiv_id"])
        print(f"Resuming: {len(done_ids)} papers already processed.")

    rows = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Phase 4 corpus scan"):
        arxiv_id = row["arxiv_id"]
        if arxiv_id in done_ids:
            continue

        text = fetch_fulltext(arxiv_id)
        if text is None:
            rows.append({"arxiv_id": arxiv_id, "status": "no_fulltext"})
            continue

        try:
            applic_response = call_llm(client, APPLICABILITY_PROMPT, text, max_tokens=100)
            applicability = parse_applicability(applic_response)
        except Exception as e:
            rows.append({"arxiv_id": arxiv_id, "status": f"applicability_error: {e}"})
            continue

        record = {"arxiv_id": arxiv_id, "status": "ok", "applicability": applicability}

        if applicability == "applicable":
            try:
                checklist_response = call_llm(client, EXTRACTION_PROMPT, text, max_tokens=1024)
                preds = parse_llm_response(checklist_response)
                for col in CHECKLIST_COLS:
                    record[col] = preds[col]
            except Exception as e:
                record["status"] = f"checklist_error: {e}"

        rows.append(record)

        # Write incrementally every 10 papers so a long run isn't lost.
        if len(rows) % 10 == 0:
            _flush(rows, OUT_PATH)
            rows = []

        time.sleep(0.5)

    if rows:
        _flush(rows, OUT_PATH)

    summarize()


def _flush(rows: list, path: Path):
    new_df = pd.DataFrame(rows)
    if path.exists():
        existing = pd.read_csv(path, dtype=str)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(path, index=False)


def summarize():
    if not OUT_PATH.exists():
        print("No results to summarize.")
        return

    df = pd.read_csv(OUT_PATH, dtype=str).fillna("")
    n_total = len(df)
    n_ok = (df["status"] == "ok").sum()
    n_applicable = (df["applicability"] == "applicable").sum()
    n_not_applicable = (df["applicability"] == "not_applicable").sum()

    print(f"\n{'=' * 70}")
    print("PHASE 4: CORPUS-SCALE SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total papers scanned: {n_total}")
    print(f"Successfully processed: {n_ok}")
    print(f"Judged applicable: {n_applicable} ({n_applicable/n_ok*100:.1f}% of processed)")
    print(f"Judged not_applicable: {n_not_applicable} ({n_not_applicable/n_ok*100:.1f}% of processed)")
    print(f"\nApplicability screen validated at: accuracy={APPLICABILITY_VALIDATION['accuracy']}, "
          f"precision={APPLICABILITY_VALIDATION['precision']}, recall={APPLICABILITY_VALIDATION['recall']} "
          f"(against 50-paper gold set, notes/008)")

    applicable_df = df[df["applicability"] == "applicable"]
    print(f"\n{'=' * 70}")
    print("DISCLOSURE RATES AMONG PAPERS JUDGED APPLICABLE")
    print("(qualified by each element's own validated precision/recall -- notes/006)")
    print(f"{'=' * 70}")
    for col in CHECKLIST_COLS:
        if col not in applicable_df.columns:
            continue
        counts = applicable_df[col].value_counts()
        n_disclosed = counts.get("disclosed", 0)
        n_absent = counts.get("absent", 0)
        n_element_total = n_disclosed + n_absent
        rate = n_disclosed / n_element_total * 100 if n_element_total > 0 else float("nan")
        val = CHECKLIST_VALIDATION[col]
        val_str = (f"validated precision={val['precision']}, recall={val['recall']}"
                   if val["precision"] is not None else "UNVALIDATED (n=1 in gold set, unscoreable)")
        print(f"\n{col}: {n_disclosed}/{n_element_total} disclosed ({rate:.1f}%)")
        print(f"  [{val_str}]")

    print(f"\n{'=' * 70}")
    print("This is a raw disclosure-rate estimate over the scanned corpus,")
    print("qualified by known detector precision/recall -- NOT a corrected")
    print("or debiased population estimate. See notes/008 for full caveats.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
