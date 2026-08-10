"""
phase2_classifier.py

Phase 2: LLM-based extraction classifier, prompted against the same
five checklist criteria used for hand-labeling, scored head-to-head
against the Phase 1 keyword baseline on the same 33 applicable papers.

Uses the Anthropic API via the official anthropic Python SDK -- not
fine-tuning. A fine-tuned transformer was considered and deferred, see
ISSUES.md, because the current gold set is far too small to fine-tune
on without just memorizing it. A free-tier Gemini approach was also
tried first and abandoned after repeated ACCESS_TOKEN_TYPE_UNSUPPORTED
errors traced to a known issue with newer "AQ."-prefixed Gemini auth
keys as of mid-2026 -- not fixable from the client side. See ISSUES.md.

Requires an Anthropic API key (from console.anthropic.com, a paid,
pay-per-use account separate from any claude.ai subscription) in the
environment:
    export ANTHROPIC_API_KEY=sk-ant-...
or in a .env file (loaded via python-dotenv) as:
    ANTHROPIC_API_KEY=sk-ant-...

Writes:
    results/phase2_predictions.csv  -- per-paper, per-element prediction vs. gold label
    results/phase2_scores.csv       -- per-element precision/recall/F1
    results/phase1_vs_phase2.csv    -- side-by-side comparison

Usage:
    python src/phase2_classifier.py
"""

import os
import re
import time
from pathlib import Path

import anthropic
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

GOLD_PATH = Path("data/gold_set/gold_set_sample.csv")
RESULTS_DIR = Path("results")

AR5IV_URL = "https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
MODEL = "claude-sonnet-4-6"

CHECKLIST_COLS = [
    "walk_forward_validation",
    "purged_embargoed_cv",
    "out_of_sample_cost_modeling",
    "multiple_testing_correction",
    "multi_window_validation",
]

# Definitions kept consistent with the labeling decisions actually made
# by hand -- see notes/001, notes/004, notes/005. In particular:
# - "not_applicable" is not offered here; Phase 2, like Phase 1, is only
#   scored on papers already judged applicable by a human.
# - multi_window_validation explicitly requires DISTINCT, separately
#   identified historical periods -- NOT a single continuous rolling/
#   walk-forward process by itself (see notes/005: this distinction was
#   learned the hard way after a bad assumption in Phase 1).
# - out_of_sample_cost_modeling counts slippage modeling alone as
#   sufficient, even without separately modeling fees/spread/impact
#   (see notes/004).
EXTRACTION_PROMPT = """You are checking a quantitative finance paper's methodology section for five specific, checkable disclosures. For each one, answer strictly "disclosed" or "absent" based only on what the text explicitly states -- do not infer or assume.

Definitions (apply these exactly, they are more specific than the plain English terms suggest):

1. walk_forward_validation: the paper describes repeatedly retraining/re-estimating the model forward through time (rolling or expanding window), not just a single static train/test split.

2. purged_embargoed_cv: the paper explicitly describes a gap enforced between training and test data to prevent leakage (purging or embargo), not just any train/test split.

3. out_of_sample_cost_modeling: the paper models at least one of transaction fees, bid-ask spread, slippage, or market impact, and applies it to the reported out-of-sample results. A paper merely mentioning that costs "should be" or "would need to be" modeled as future work does NOT count -- that is an explicit statement of absence, not disclosure.

4. multiple_testing_correction: the paper applies a statistical correction (e.g. Bonferroni, false discovery rate, family-wise error control, Model Confidence Set) when comparing multiple strategies, parameters, or assets.

5. multi_window_validation: the paper tests performance on more than one DISTINCT, separately-identified historical period. This includes fold-based or periodic walk-forward designs where the paper reports a countable number of distinct windows/folds (e.g. "5 folds," "32 weekly re-calibrations," "10 folds advanced in 6-month steps") -- these DO count, because the periods are discrete and enumerable even though they arise from a walk-forward protocol. This does NOT include a single continuous rolling or expanding-window re-estimation process with no discrete, countable periods identified (e.g. re-estimating daily over one continuous multi-year span with no named folds or distinct blocks) -- that is walk-forward validation but not, by itself, multi-window validation. The distinguishing question is: does the paper name or count a specific number of distinct periods/folds/windows? If yes, multi-window applies. If it's just "re-estimated every day/week over years X-Y" with no discrete count, it does not.

For each of the five, output exactly one line in this format, nothing else:
element_name: disclosed
or
element_name: absent

Paper text follows:

---
{paper_text}
---
"""


def fetch_fulltext(arxiv_id: str) -> str | None:
    url = AR5IV_URL.format(arxiv_id=arxiv_id)
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "systematic-uncertainty-research/0.1"})
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup.find_all(["bibliography", "table"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def call_llm(client: anthropic.Anthropic, paper_text: str, max_chars: int = 150000, max_retries: int = 3) -> str:
    """Calls the Anthropic API with the extraction prompt via the official
    SDK. Truncates very long papers to max_chars (naive character cutoff,
    a known limitation). Retries with backoff on rate-limit errors."""
    truncated = paper_text[:max_chars]
    prompt = EXTRACTION_PROMPT.format(paper_text=truncated)

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(block.text for block in response.content if hasattr(block, "text"))
        except anthropic.RateLimitError:
            wait = 15 * (attempt + 1)
            print(f"    Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue

    raise RuntimeError(f"Still rate-limited after {max_retries} retries")


def parse_llm_response(response_text: str) -> dict:
    """Parses the five 'element_name: disclosed/absent' lines. Any
    element not found in the response is marked 'absent' by default
    (fails closed, not open) with a note printed to console."""
    preds = {}
    for col in CHECKLIST_COLS:
        match = re.search(rf"{col}\s*:\s*(disclosed|absent)", response_text, flags=re.IGNORECASE)
        if match:
            preds[col] = match.group(1).lower()
        else:
            preds[col] = "absent"
            print(f"    WARNING: could not parse '{col}' from LLM response, defaulting to absent")
    return preds


def score_element(gold: pd.Series, pred: pd.Series) -> dict:
    mask = gold.isin(["disclosed", "absent"])
    g, p = gold[mask], pred[mask]

    tp = ((g == "disclosed") & (p == "disclosed")).sum()
    fp = ((g == "absent") & (p == "disclosed")).sum()
    fn = ((g == "disclosed") & (p == "absent")).sum()
    tn = ((g == "absent") & (p == "absent")).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if precision == precision and recall == recall and (precision + recall) > 0
          else float("nan"))

    n_ambiguous = (gold == "ambiguous").sum()

    return {
        "n_scored": int(mask.sum()),
        "n_ambiguous_excluded": int(n_ambiguous),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "precision": round(precision, 3) if precision == precision else None,
        "recall": round(recall, 3) if recall == recall else None,
        "f1": round(f1, 3) if f1 == f1 else None,
    }


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "\nANTHROPIC_API_KEY not set. Get a key at console.anthropic.com "
            "(separate, pay-per-use account -- not your claude.ai login), then:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "or add it to a .env file in the repo root.\n"
        )

    client = anthropic.Anthropic(api_key=api_key)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(GOLD_PATH, dtype=str).fillna("")
    applicable = df[~(df[CHECKLIST_COLS] == "not_applicable").all(axis=1)].copy()
    print(f"{len(df)} total papers, {len(applicable)} applicable, scoring those.\n")

    pred_rows = []
    for _, row in tqdm(applicable.iterrows(), total=len(applicable), desc="Phase 2 (LLM)"):
        arxiv_id = row["arxiv_id"]
        text = fetch_fulltext(arxiv_id)
        if text is None:
            print(f"  WARNING: no full text for {arxiv_id}, skipping.")
            continue

        try:
            response_text = call_llm(client, text)
        except Exception as e:
            print(f"  ERROR calling API for {arxiv_id}: {e}, skipping.")
            continue

        if not response_text:
            print(f"  WARNING: empty response for {arxiv_id}, skipping.")
            continue

        preds = parse_llm_response(response_text)
        record = {"arxiv_id": arxiv_id}
        for col in CHECKLIST_COLS:
            record[f"{col}__gold"] = row[col]
            record[f"{col}__pred"] = preds[col]
        pred_rows.append(record)
        time.sleep(0.5)

    pred_df = pd.DataFrame(pred_rows)
    pred_path = RESULTS_DIR / "phase2_predictions.csv"
    pred_df.to_csv(pred_path, index=False)
    print(f"\nWrote per-paper predictions to {pred_path}")

    score_rows = []
    for col in CHECKLIST_COLS:
        scores = score_element(pred_df[f"{col}__gold"], pred_df[f"{col}__pred"])
        scores["element"] = col
        score_rows.append(scores)

    score_df = pd.DataFrame(score_rows)[
        ["element", "n_scored", "n_ambiguous_excluded", "tp", "fp", "fn", "tn",
         "precision", "recall", "f1"]
    ]
    score_path = RESULTS_DIR / "phase2_scores.csv"
    score_df.to_csv(score_path, index=False)

    print(f"\n{'=' * 70}")
    print("PHASE 2 SCORES (LLM extraction classifier, Claude)")
    print(f"{'=' * 70}")
    print(score_df.to_string(index=False))
    print(f"\nWrote scores to {score_path}")

    phase1_path = RESULTS_DIR / "phase1_scores.csv"
    if phase1_path.exists():
        p1 = pd.read_csv(phase1_path).set_index("element")[["precision", "recall", "f1"]]
        p2 = score_df.set_index("element")[["precision", "recall", "f1"]]
        comparison = p1.join(p2, lsuffix="_phase1", rsuffix="_phase2")
        comp_path = RESULTS_DIR / "phase1_vs_phase2.csv"
        comparison.to_csv(comp_path)
        print(f"\n{'=' * 70}")
        print("PHASE 1 vs PHASE 2")
        print(f"{'=' * 70}")
        print(comparison.to_string())
        print(f"\nWrote comparison to {comp_path}")
    else:
        print("\nNOTE: results/phase1_scores.csv not found -- run phase1_detector.py "
              "first for a side-by-side comparison.")


if __name__ == "__main__":
    main()