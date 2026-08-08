"""
label_gold_set.py

Interactive CLI for hand-labeling the gold set. Walks through each paper
one at a time: shows title/abstract/PDF link, asks an applicability
question first, then (only if applicable) asks disclosed/absent/ambiguous
for each of the five checklist elements. Saves to the CSV after every
single paper, so nothing is lost if you stop partway through.

Resumable: papers that already have a non-empty value in every checklist
column are skipped automatically. Re-run any time to pick up where you
left off.

This does not read the paper for you -- open the PDF link yourself
(and/or the matching excerpt file in data/gold_set/excerpts/) before
answering. This script is bookkeeping, not judgment.

Usage:
    python src/label_gold_set.py
"""

import sys
from pathlib import Path

import pandas as pd

GOLD_PATH = Path("data/gold_set/gold_set_sample.csv")
EXCERPT_DIR = Path("data/gold_set/excerpts")

CHECKLIST_COLS = [
    "walk_forward_validation",
    "purged_embargoed_cv",
    "out_of_sample_cost_modeling",
    "multiple_testing_correction",
    "multi_window_validation",
]

VALID_STATES = {
    "1": "disclosed",
    "2": "absent",
    "3": "ambiguous",
}

STATE_PROMPT = "  [1] disclosed  [2] absent  [3] ambiguous  > "


def is_labeled(row) -> bool:
    return all(str(row.get(col, "")).strip() != "" for col in CHECKLIST_COLS)


def ask(prompt: str, valid: dict) -> str:
    # Normalize input: lowercase, strip whitespace, strip brackets/punctuation
    # someone might echo back from the prompt itself (e.g. "[y]", "y.", "Y").
    while True:
        raw = input(prompt).strip()
        ans = raw.lower().strip("[]. ")
        if ans in valid:
            return valid[ans]
        if ans in ("q", "quit"):
            print("\nStopping. Progress so far is already saved to disk.")
            sys.exit(0)
        # also accept the full word if it uniquely matches one option's value
        word_matches = [v for k, v in valid.items() if str(v).lower().startswith(ans) and ans]
        if len(word_matches) == 1:
            return word_matches[0]
        print(f"  Not a valid option ('{raw}'). Try again (or 'q' to quit).")


def label_paper(df: pd.DataFrame, idx: int) -> None:
    row = df.loc[idx]
    arxiv_id = row["arxiv_id"]
    excerpt_path = EXCERPT_DIR / f"{arxiv_id.replace('/', '_')}.md"

    print("\n" + "=" * 70)
    print(f"[{idx + 1}/{len(df)}]  {arxiv_id}")
    print(row["title"])
    print("-" * 70)
    print(row["abstract"][:500] + ("..." if len(row["abstract"]) > 500 else ""))
    print("-" * 70)
    print(f"PDF:      {row['pdf_url']}")
    print(f"Excerpts: {excerpt_path}")
    print("=" * 70)

    applicable = ask(
        "\nDoes this paper report empirical/backtested predictive results "
        "at all (not just descriptive stats or a non-empirical framework)?\n"
        "  [y] yes, applicable   [n] no, not applicable   > ",
        {"y": True, "n": False},
    )

    if not applicable:
        for col in CHECKLIST_COLS:
            df.at[idx, col] = "not_applicable"
        df.at[idx, "notes"] = input(
            "Optional note on why this is not_applicable (enter to skip): "
        ).strip()
    else:
        for col in CHECKLIST_COLS:
            print(f"\n{col}:")
            df.at[idx, col] = ask(STATE_PROMPT, VALID_STATES)
        df.at[idx, "notes"] = input(
            "\nOptional note (phrasing found, anything unusual; enter to skip): "
        ).strip()

    labeled_by = input("Labeled by (enter to skip): ").strip()
    if labeled_by:
        df.at[idx, "labeled_by"] = labeled_by
    df.at[idx, "label_date"] = pd.Timestamp.now().strftime("%Y-%m-%d")

    df.to_csv(GOLD_PATH, index=False)
    print("Saved.")


def main():
    if not GOLD_PATH.exists():
        raise FileNotFoundError(f"{GOLD_PATH} not found. Run pull_arxiv.py first.")

    df = pd.read_csv(GOLD_PATH, dtype=str).fillna("")

    remaining = [i for i in df.index if not is_labeled(df.loc[i])]
    if not remaining:
        print("All papers already labeled. Nothing to do.")
        return

    print(f"{len(df) - len(remaining)}/{len(df)} papers already labeled.")
    print(f"{len(remaining)} remaining. Type 'q' at any prompt to stop and save.\n")

    for idx in remaining:
        label_paper(df, idx)

    print("\nAll papers labeled.")


if __name__ == "__main__":
    main()