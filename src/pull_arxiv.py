"""
pull_arxiv.py

Pulls paper metadata from arXiv for the q-fin.ST category (quantitative
finance, statistical finance). Other q-fin categories (q-fin.CP, q-fin.TR,
q-fin.PM) are an open item -- deferred for now, see notes/.

Pulls are pinned to an explicit, fixed submission-date window (not
"most recent N as of whenever this runs"), so re-running this script
produces the same underlying pool of papers every time, and --seed then
makes the gold-set sample from that pool reproducible too. Without the
date pin, "most recent 500" silently drifts every time arXiv publishes
something new, which defeats the point of a fixed seed -- see
notes/002_reproducibility_date_window.md.

Writes:
    data/raw/qfin_st_metadata.csv   -- full pulled metadata
    data/gold_set/gold_set_sample.csv -- random sample for hand-labeling

Usage:
    python src/pull_arxiv.py --max-results 500 --gold-size 50
    python src/pull_arxiv.py --start-date 2024-01-01 --end-date 2026-08-01
"""

import argparse
import random
from datetime import datetime
from pathlib import Path

import arxiv
import pandas as pd
from tqdm import tqdm

CATEGORY = "q-fin.ST"

# Fixed default window -- change deliberately, not by re-running on a
# different day. Any change to these defaults should get a notes/ entry
# since it changes what the gold set's random sample is drawn from.
DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE = "2026-08-01"

RAW_DIR = Path("data/raw")
GOLD_DIR = Path("data/gold_set")


def fetch_metadata(max_results: int, start_date: str, end_date: str) -> pd.DataFrame:
    """Query arXiv for the given category within a fixed submission-date
    window, most recent first within that window. The date window is
    what makes this reproducible -- max_results alone is not enough,
    since "top N most recent" drifts as arXiv publishes new papers."""
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)

    date_filter = f"submittedDate:[{start_date.replace('-', '')}0000 TO {end_date.replace('-', '')}2359]"
    query = f"cat:{CATEGORY} AND {date_filter}"

    search = arxiv.Search(
        query=query,
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
    parser.add_argument("--start-date", type=str, default=DEFAULT_START_DATE,
                         help="Submission date window start, YYYY-MM-DD. "
                              "Fixed by default for reproducibility -- see module docstring.")
    parser.add_argument("--end-date", type=str, default=DEFAULT_END_DATE,
                         help="Submission date window end, YYYY-MM-DD.")
    args = parser.parse_args()

    # Validate date format early, fail loudly rather than sending a malformed
    # query to arXiv and getting a confusing empty result back.
    for label, val in [("--start-date", args.start_date), ("--end-date", args.end_date)]:
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            raise SystemExit(f"{label}='{val}' is not a valid YYYY-MM-DD date.")

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

    print(f"Pulling up to {args.max_results} papers from {CATEGORY} "
          f"({args.start_date} to {args.end_date})...")
    df = fetch_metadata(args.max_results, args.start_date, args.end_date)

    raw_path = RAW_DIR / "qfin_st_metadata.csv"
    df.to_csv(raw_path, index=False)
    print(f"Wrote {len(df)} rows to {raw_path}")

    if len(df) < args.max_results:
        print(f"NOTE: only {len(df)} papers found in this date window, "
              f"fewer than --max-results={args.max_results}. The pool this "
              "gold set is sampled from is smaller than requested -- this is "
              "fine but worth knowing.")

    gold_df = build_gold_sample(df, args.gold_size, seed=args.seed)
    gold_df.to_csv(gold_path, index=False)
    print(f"Wrote {len(gold_df)} rows to {gold_path} (ready for hand-labeling)")


if __name__ == "__main__":
    main()