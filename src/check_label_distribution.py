"""
check_label_distribution.py

Quick sanity check on the hand-labeled gold set: value counts per
checklist column, plus a few consistency checks (e.g. any row with a
mix of not_applicable and a real label, which would indicate a labeling
slip rather than a genuine judgment).

Usage:
    python src/check_label_distribution.py
"""

from pathlib import Path

import pandas as pd

GOLD_PATH = Path("data/gold_set/gold_set_sample.csv")

CHECKLIST_COLS = [
    "walk_forward_validation",
    "purged_embargoed_cv",
    "out_of_sample_cost_modeling",
    "multiple_testing_correction",
    "multi_window_validation",
]


def main():
    df = pd.read_csv(GOLD_PATH, dtype=str).fillna("")

    print(f"Total papers: {len(df)}\n")

    print("=" * 60)
    print("VALUE COUNTS PER ELEMENT")
    print("=" * 60)
    for col in CHECKLIST_COLS:
        print(f"\n{col}:")
        counts = df[col].value_counts(dropna=False)
        for val, n in counts.items():
            label = val if val else "(blank -- unlabeled!)"
            print(f"  {label:20s} {n:3d}  ({n/len(df)*100:.0f}%)")

    print("\n" + "=" * 60)
    print("PAPER-LEVEL APPLICABILITY")
    print("=" * 60)
    # A paper is "not_applicable" overall if ALL 5 columns are not_applicable.
    # Anything else with a mix is worth a look -- either a genuinely mixed
    # case (fine) or a labeling slip (worth checking).
    def classify(row):
        vals = set(row[col] for col in CHECKLIST_COLS)
        if vals == {"not_applicable"}:
            return "fully not_applicable"
        elif "not_applicable" in vals and len(vals) > 1:
            return "MIXED (na + real label)"
        elif "" in vals:
            return "INCOMPLETE (blank cell)"
        else:
            return "fully applicable"

    df["_classification"] = df.apply(classify, axis=1)
    print(df["_classification"].value_counts().to_string())

    mixed = df[df["_classification"] == "MIXED (na + real label)"]
    if len(mixed) > 0:
        print(f"\n{len(mixed)} paper(s) with a mix of not_applicable and a real "
              "label across the 5 elements -- worth a quick look, this can be "
              "a genuine judgment call (e.g. cost modeling n/a but walk-forward "
              "applicable) or a labeling slip:")
        for _, row in mixed.iterrows():
            print(f"  {row['arxiv_id']}: " +
                  ", ".join(f"{c}={row[c]}" for c in CHECKLIST_COLS))

    incomplete = df[df["_classification"] == "INCOMPLETE (blank cell)"]
    if len(incomplete) > 0:
        print(f"\n{len(incomplete)} paper(s) with at least one blank checklist "
              "cell -- these weren't fully labeled:")
        for _, row in incomplete.iterrows():
            print(f"  {row['arxiv_id']}")

    print("\n" + "=" * 60)
    print("NOTES FIELD COVERAGE")
    print("=" * 60)
    has_notes = (df["notes"].str.strip() != "").sum()
    print(f"{has_notes}/{len(df)} papers have a non-empty note.")


if __name__ == "__main__":
    main()