# 003 — Gold set labeling complete: baseline disclosure rates

**Date:** 2026-08-07

**Question:** After hand-labeling all 50 papers in the gold set (arXiv
q-fin.ST, fixed date window 2020-01-01 to 2026-08-01, seed 42), what
does the ground-truth disclosure picture actually look like? This is
the number Phase 1's keyword detector needs to be checked against, not
a finding about the detector itself -- the detector doesn't exist yet.

**Method:** Full manual read of each paper's methodology/results
section via `src/label_gold_set.py`, using the four-state schema
(disclosed / absent / ambiguous / not_applicable) established in
notes/001. Applicability judged first per paper (does it report real
empirical/backtested predictive results at all), then each of the five
checklist elements judged only for papers where the checklist applies.
Sanity-checked with `src/check_label_distribution.py` -- no blank
cells, no inconsistent mixed rows, all 50 have notes.

**Result:**

17/50 papers (34%) are fully not_applicable -- governance frameworks,
descriptive/statistical-properties studies (entropy, multifractal
analysis), theoretical derivations with no backtest attached.

Among the 33/50 papers (66%) where the checklist genuinely applies
(real predictive/empirical claims):

| Element | Disclosed | Absent | Ambiguous |
|---|---|---|---|
| Walk-forward validation | 13 (39%) | 20 (61%) | 0 |
| Purged/embargoed CV | 1 (3%) | 32 (97%) | 0 |
| Out-of-sample cost modeling | 6 (18%) | 25 (76%) | 2 (6%) |
| Multiple-testing correction | 4 (12%) | 29 (88%) | 0 |
| Multi-window validation | 11 (33%) | 22 (67%) | 0 |

Purged/embargoed CV and multiple-testing correction are disclosed at
the lowest rates by a wide margin -- almost no paper in this sample
mentions a train/test gap for leakage prevention, and multi-comparison
correction is nearly as rare.

**Caveats, stated explicitly:**

- N=33 for "applicable" papers is small. These percentages are
  directional, not precise -- wide confidence intervals at this sample
  size. Do not present these as field-wide statistics without that
  caveat; that's exactly the kind of overclaim Section 7 of the
  proposal rules out.
- This is a single labeler's judgment (one person, no inter-rater
  check). A second labeler cross-checking a subset would strengthen
  this, but is not currently planned -- worth reconsidering if this
  number is used publicly.
- Corpus is q-fin.ST only, one fixed date window. Does not generalize
  to q-fin.CP/TR/PM or to other date ranges without saying so.

**Why this matters for Phase 1:** this table is the actual scoring
target. A keyword detector that reproduces roughly this shape (few
papers flagged for purged CV or multiple-testing disclosure, more
flagged for walk-forward) on the same 33 applicable papers would be
doing its job. A detector that finds wildly different rates needs
investigation before being trusted.

**Reproduction:**
    python src/pull_arxiv.py --max-results 500 --gold-size 50 --seed 42
    python src/triage_gold_set.py
    python src/label_gold_set.py   # hand-labeling, not automated
    python src/check_label_distribution.py
