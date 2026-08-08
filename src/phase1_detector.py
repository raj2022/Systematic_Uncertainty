"""
phase1_detector.py

Phase 1 baseline: a simple keyword/phrase detector, scored against the
hand-labeled gold set. This is the number everything more sophisticated
(Phase 2's classifier) has to beat -- see proposal, section 6.

Detection rule (deliberately simple): for each of the five checklist
elements, if any of that element's regex patterns match anywhere in the
paper's full text, predict "disclosed"; otherwise predict "absent".
This detector does NOT attempt to judge applicability -- that's a scope
decision, stated explicitly in the results output. It is scored only
against the subset of gold-set papers a human already marked as
applicable (i.e. not_applicable papers are excluded from scoring, not
silently treated as a correct "absent" prediction).

"Ambiguous" gold labels are also excluded from precision/recall scoring
per element (the detector isn't being asked to output "ambiguous"), but
their count is reported separately so they aren't silently dropped from
view.

Writes:
    results/phase1_scores.csv       -- per-element precision/recall/F1
    results/phase1_predictions.csv  -- per-paper, per-element prediction vs. gold label

Usage:
    python src/phase1_detector.py
"""

import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

GOLD_PATH = Path("data/gold_set/gold_set_sample.csv")
RESULTS_DIR = Path("results")

AR5IV_URL = "https://ar5iv.labs.arxiv.org/html/{arxiv_id}"

# Same patterns as triage_gold_set.py -- kept in sync deliberately. If you
# edit one, edit the other, or better, factor both into a shared module
# (tracked as an open item, see ISSUES.md).
CHECKLIST_PATTERNS = {
    "walk_forward_validation": [
        r"walk[\s-]?forward",
        r"rolling[\s-]?window\s+(validation|evaluation|test)",
        r"expanding[\s-]?window",
    ],
    "purged_embargoed_cv": [
        r"purged\s+cross[\s-]?validation",
        r"embargo(ed)?",
        r"purg(e|ed|ing)\s+.{0,20}(cross[\s-]?validation|fold)",
    ],
    "out_of_sample_cost_modeling": [
        r"transaction\s+cost",
        r"out[\s-]?of[\s-]?sample\s+.{0,20}cost",
        r"slippage",
        r"bid[\s-]?ask\s+spread",
        r"market\s+impact",
    ],
    "multiple_testing_correction": [
        r"multiple[\s-]?(testing|comparisons?)",
        r"bonferroni",
        r"false\s+discovery\s+rate",
        r"family[\s-]?wise\s+error",
        r"data[\s-]?snoop(ing)?",
    ],
    "multi_window_validation": [
        r"multiple\s+(time\s+)?(periods?|windows?|regimes?)",
        r"out[\s-]?of[\s-]?sample\s+period",
        r"second\s+(window|period|dataset)",
        r"robustness\s+.{0,20}(period|window|sample)",
    ],
}

CHECKLIST_COLS = list(CHECKLIST_PATTERNS.keys())


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


def predict(text: str) -> dict:
    """disclosed if any pattern for that element matches, else absent."""
    preds = {}
    for element, patterns in CHECKLIST_PATTERNS.items():
        hit = any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)
        preds[element] = "disclosed" if hit else "absent"
    return preds


def score_element(gold: pd.Series, pred: pd.Series) -> dict:
    """Precision/recall/F1 for the 'disclosed' class, on rows where gold
    is disclosed or absent (ambiguous rows excluded, counted separately)."""
    mask = gold.isin(["disclosed", "absent"])
    g, p = gold[mask], pred[mask]

    tp = ((g == "disclosed") & (p == "disclosed")).sum()
    fp = ((g == "absent") & (p == "disclosed")).sum()
    fn = ((g == "disclosed") & (p == "absent")).sum()
    tn = ((g == "absent") & (p == "absent")).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall and (precision + recall) > 0 else float("nan"))

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
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(GOLD_PATH, dtype=str).fillna("")

    # Scope decision: Phase 1 is only scored on papers a human already
    # marked applicable. Applicability detection is not this phase's job.
    applicable = df[~(df[CHECKLIST_COLS] == "not_applicable").all(axis=1)].copy()
    n_not_applicable = len(df) - len(applicable)
    print(f"{len(df)} total papers, {n_not_applicable} not_applicable (excluded from scoring), "
          f"{len(applicable)} scored.\n")

    pred_rows = []
    for _, row in tqdm(applicable.iterrows(), total=len(applicable), desc="Scoring"):
        arxiv_id = row["arxiv_id"]
        text = fetch_fulltext(arxiv_id)
        if text is None:
            print(f"  WARNING: no full text for {arxiv_id}, skipping this paper.")
            continue
        preds = predict(text)
        record = {"arxiv_id": arxiv_id}
        for col in CHECKLIST_COLS:
            record[f"{col}__gold"] = row[col]
            record[f"{col}__pred"] = preds[col]
        pred_rows.append(record)
        time.sleep(1)

    pred_df = pd.DataFrame(pred_rows)
    pred_path = RESULTS_DIR / "phase1_predictions.csv"
    pred_df.to_csv(pred_path, index=False)
    print(f"\nWrote per-paper predictions to {pred_path}")

    score_rows = []
    for col in CHECKLIST_COLS:
        gold = pred_df[f"{col}__gold"]
        pred = pred_df[f"{col}__pred"]
        scores = score_element(gold, pred)
        scores["element"] = col
        score_rows.append(scores)

    score_df = pd.DataFrame(score_rows)[
        ["element", "n_scored", "n_ambiguous_excluded", "tp", "fp", "fn", "tn",
         "precision", "recall", "f1"]
    ]
    score_path = RESULTS_DIR / "phase1_scores.csv"
    score_df.to_csv(score_path, index=False)

    print(f"\n{'=' * 70}")
    print("PHASE 1 BASELINE SCORES (keyword/phrase detector)")
    print(f"{'=' * 70}")
    print(score_df.to_string(index=False))
    print(f"\nWrote scores to {score_path}")


if __name__ == "__main__":
    main()
