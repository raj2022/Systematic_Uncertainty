"""
phase4_applicability_validation.py

Phase 4, step 1: before scaling Phase 2 to the full ~500-paper raw
corpus, validate whether an LLM can correctly judge APPLICABILITY
(does this paper report real empirical/backtested predictive results
at all) -- a judgment that, until now, was made entirely by hand for
all 50 gold-set papers. Phase 1 and Phase 2 have only ever been asked
to predict the five checklist elements on papers a human already
filtered to "applicable."

Runs an applicability-only prompt against all 50 gold-set papers
(not just the 33 applicable ones -- this needs the full set, including
the 17 not_applicable papers, to test the classifier's ability to
distinguish both classes) and scores against the existing hand labels.

Writes:
    results/phase4_applicability_validation.csv
    results/phase4_applicability_scores.csv

Usage:
    python src/phase4_applicability_validation.py
"""

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
from phase2_classifier import CHECKLIST_COLS, MODEL

load_dotenv()

GOLD_PATH = Path("data/gold_set/gold_set_sample.csv")
RESULTS_DIR = Path("results")

APPLICABILITY_PROMPT = """You are screening a quantitative finance paper to determine if it reports real empirical or backtested predictive results.

A paper is APPLICABLE only if it evaluates a model, strategy, or forecast on HELD-OUT data it was not fit/trained/calibrated on, and reports quantitative out-of-sample performance results (e.g. out-of-sample accuracy, Sharpe ratio, returns, forecast error on a genuinely separate test period or sample).

A paper is NOT_APPLICABLE if it does not meet that bar -- even if it reports substantial quantitative or statistical results. In particular, the following are NOT_APPLICABLE even though they involve real data, models, and numbers:
- A theoretical or statistical model FIT or CALIBRATED to real financial data, reporting in-sample fit statistics (parameter estimates, confidence intervals, in-sample RMSE, MLE variance) with no held-out/out-of-sample test.
- A paper reporting Granger-causality, correlation, or other statistical-inference results (p-values, bootstrap confidence intervals) describing relationships in historical data, with no forecast evaluated out of sample.
- A model (e.g. a fine-tuned classifier) where the data is split into train/validation/test, but no held-out performance metric for that model is actually reported -- only in-sample or descriptive results.
- A governance/policy framework paper, a purely descriptive statistical-properties study (entropy, multifractal analysis) with no predictive model, a survey, or a discretionary case study with no trained model or backtest.

The single most important question: does the paper report a genuine OUT-OF-SAMPLE performance number, not just a well-fit model or interesting statistical relationship? If no, answer not_applicable, regardless of how much quantitative content the paper contains.

NOTE ON A KNOWN LIMITATION OF THIS RULE: some genuine backtest/strategy
papers evaluate performance on the full available sample rather than a
true held-out split (e.g. computing statistics over the whole dataset,
or using bootstrap resampling of the same sample rather than an
out-of-sample test). Strictly, such papers ARE proposing and evaluating
a real trading/forecasting strategy and arguably should be applicable,
with their lack of held-out evaluation flagged separately as an absent
walk-forward/multi-window disclosure rather than excluded from
screening entirely. This prompt intentionally uses the stricter,
held-out-required rule anyway, because it was found to score better
against hand labels overall on validation testing (higher accuracy and
F1) despite this known conceptual imperfection -- see notes/008 for
the full comparison and reasoning. Apply the rule AS WRITTEN above.

Answer with exactly one line, nothing else:
applicability: applicable
or
applicability: not_applicable

Paper text follows:

---
{paper_text}
---
"""


def call_llm(client: anthropic.Anthropic, text: str, max_chars: int = 60000, max_retries: int = 3) -> str:
    truncated = text[:max_chars]
    prompt = APPLICABILITY_PROMPT.format(paper_text=truncated)
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in response.content if hasattr(b, "text"))
        except anthropic.RateLimitError:
            wait = 15 * (attempt + 1)
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
    raise RuntimeError("Still rate-limited after retries")


def parse_applicability(response_text: str) -> str:
    match = re.search(r"applicability\s*:\s*(applicable|not_applicable)", response_text, flags=re.IGNORECASE)
    if match:
        return match.group(1).lower()
    print(f"    WARNING: could not parse applicability from: {response_text[:100]}")
    return "applicable"  # fail open here deliberately -- see notes/008: for
    # this specific screening step, defaulting to "applicable" on a parse
    # failure means the paper still gets the full checklist treatment
    # (safer than silently dropping it from the corpus-scale estimate)


def gold_applicability(row: pd.Series) -> str:
    """A paper is applicable in the gold labels if NOT all 5 checklist
    columns are 'not_applicable'."""
    vals = [row[c] for c in CHECKLIST_COLS]
    return "not_applicable" if all(v == "not_applicable" for v in vals) else "applicable"


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set.")
    client = anthropic.Anthropic(api_key=api_key)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(GOLD_PATH, dtype=str).fillna("")
    df["gold_applicability"] = df.apply(gold_applicability, axis=1)

    print(f"Testing applicability classification on all {len(df)} gold-set papers "
          f"({(df['gold_applicability'] == 'applicable').sum()} applicable, "
          f"{(df['gold_applicability'] == 'not_applicable').sum()} not_applicable per hand labels)\n")

    rows = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Applicability check"):
        arxiv_id = row["arxiv_id"]
        text = fetch_fulltext(arxiv_id)
        if text is None:
            print(f"  WARNING: no full text for {arxiv_id}, skipping.")
            continue
        response = call_llm(client, text)
        pred = parse_applicability(response)
        rows.append({
            "arxiv_id": arxiv_id,
            "gold_applicability": row["gold_applicability"],
            "pred_applicability": pred,
        })
        time.sleep(0.5)

    result_df = pd.DataFrame(rows)
    out_path = RESULTS_DIR / "phase4_applicability_validation.csv"
    result_df.to_csv(out_path, index=False)
    print(f"\nWrote per-paper results to {out_path}")

    # Score treating "applicable" as the positive class
    g = result_df["gold_applicability"]
    p = result_df["pred_applicability"]
    tp = ((g == "applicable") & (p == "applicable")).sum()
    fp = ((g == "not_applicable") & (p == "applicable")).sum()
    fn = ((g == "applicable") & (p == "not_applicable")).sum()
    tn = ((g == "not_applicable") & (p == "not_applicable")).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    accuracy = (tp + tn) / len(result_df) if len(result_df) > 0 else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if precision == precision and recall == recall and (precision + recall) > 0
          else float("nan"))

    scores = pd.DataFrame([{
        "n": len(result_df), "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "accuracy": round(accuracy, 3), "precision": round(precision, 3),
        "recall": round(recall, 3), "f1": round(f1, 3),
    }])
    score_path = RESULTS_DIR / "phase4_applicability_scores.csv"
    scores.to_csv(score_path, index=False)

    print(f"\n{'=' * 60}")
    print("APPLICABILITY CLASSIFICATION SCORE (LLM vs. hand labels)")
    print(f"{'=' * 60}")
    print(scores.to_string(index=False))
    print(f"\nWrote scores to {score_path}")

    if len(result_df[g != p]) > 0:
        print(f"\n{len(result_df[g != p])} disagreement(s):")
        print(result_df[g != p].to_string(index=False))


if __name__ == "__main__":
    main()