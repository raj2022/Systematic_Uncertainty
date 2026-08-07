"""
pull_arxiv.py

Pulls paper metadata from arXiv for the q-fin.ST category (quantitative
finance, statistical finance). Other q-fin categories (q-fin.CP, q-fin.TR,
q-fin.PM) are an open item -- deferred for now, see notes/.

Writes:
    data/raw/qfin_st_metadata.csv   -- full pulled metadata
    data/gold_set/gold_set_sample.csv -- random sample for hand-labeling

Usage:
    python src/pull_arxiv.py --max-results 500 --gold-size 50
"""

import argparse
import random
from pathlib import Path

import arxiv
import pandas as pd
from tqdm import tqdm

CATEGORY = "q-fin.ST"

RAW_DIR = Path("data/raw")
GOLD_DIR = Path("data/gold_set")


def fetch_metadata(max_results: int) -> pd.DataFrame:
    """Query arXiv for the given category, most recent first."""
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)

    search = arxiv.Search(
        query=f"cat:{CATEGORY}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    rows = []
    for result in tqdm(client.results(search), total=max_results, desc="Fetching"):
        rows.append(
            {
                "arxiv_id": result.get_short_id(),
                "title": result.title.strip().replace("\n", " "),
                "abstract": result.summary.strip().replace("\n", " "),
                "authors": "; ".join(a.name for a in result.authors),
                "category": CATEGORY,
                "primary_category": result.primary_category,
                "published": result.published.isoformat(),
                "updated": result.updated.isoformat(),
                "pdf_url": result.pdf_url,
                "abs_url": result.entry_id,
            }
        )

    return pd.DataFrame(rows)


def build_gold_sample(df: pd.DataFrame, gold_size: int, seed: int = 42) -> pd.DataFrame:
    """Randomly sample papers for hand-labeling, with the four-state
    disclosure columns pre-created and left empty for manual entry."""
    if len(df) < gold_size:
        raise ValueError(
            f"Only {len(df)} papers pulled, need at least {gold_size} for gold set. "
            "Increase --max-results."
        )

    rng = random.Random(seed)
    sample_idx = rng.sample(range(len(df)), gold_size)
    sample = df.iloc[sample_idx].copy().reset_index(drop=True)

    # Disclosure checklist columns -- four-state: disclosed / absent / ambiguous / not_applicable
    # not_applicable: the paper isn't an empirical backtest at all (e.g. governance
    # frameworks, discretionary case studies, theoretical/physics-style models) --
    # distinct from "absent," which means the paper IS a backtest and should have
    # disclosed this but didn't. Conflating the two would make Phase 1's baseline
    # look like it's catching real gaps when it's actually just catching papers
    # that were never backtests to begin with. See notes/ for the decision record.
    checklist_cols = [
        "walk_forward_validation",
        "purged_embargoed_cv",
        "out_of_sample_cost_modeling",
        "multiple_testing_correction",
        "multi_window_validation",
    ]
    for col in checklist_cols:
        sample[col] = ""  # fill by hand: disclosed / absent / ambiguous / not_applicable

    sample["notes"] = ""  # free-text, per-paper reasoning for the derivation log
    sample["labeled_by"] = ""
    sample["label_date"] = ""

    return sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-results", type=int, default=500,
                         help="Number of papers to pull from q-fin.ST")
    parser.add_argument("--gold-size", type=int, default=50,
                         help="Number of papers to sample for hand-labeling")
    parser.add_argument("--seed", type=int, default=42,
                         help="Random seed for gold set sampling")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    gold_path = GOLD_DIR / "gold_set_sample.csv"
    if gold_path.exists():
        existing = pd.read_csv(gold_path)
        checklist_cols = [
            "walk_forward_validation",
            "purged_embargoed_cv",
            "out_of_sample_cost_modeling",
            "multiple_testing_correction",
            "multi_window_validation",
        ]
        has_labels = any(
            existing[col].notna().any() and (existing[col].astype(str).str.strip() != "").any()
            for col in checklist_cols
            if col in existing.columns
        )
        if has_labels:
            raise SystemExit(
                f"\n{gold_path} already exists and contains hand-entered labels.\n"
                "Refusing to overwrite. If you really want to regenerate it, "
                "move or rename the existing file first, e.g.:\n"
                f"  mv {gold_path} {gold_path.with_suffix('.bak.csv')}\n"
            )
        print(f"{gold_path} exists but has no labels yet -- safe to regenerate.")

    print(f"Pulling up to {args.max_results} papers from {CATEGORY}...")
    df = fetch_metadata(args.max_results)

    raw_path = RAW_DIR / "qfin_st_metadata.csv"
    df.to_csv(raw_path, index=False)
    print(f"Wrote {len(df)} rows to {raw_path}")

    gold_df = build_gold_sample(df, args.gold_size, seed=args.seed)
    gold_df.to_csv(gold_path, index=False)
    print(f"Wrote {len(gold_df)} rows to {gold_path} (ready for hand-labeling)")


if __name__ == "__main__":
    main()
    
    