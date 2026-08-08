# 004 — Phase 1 baseline scored; cost-modeling label rule clarified mid-review

**Date:** 2026-08-07

**Question:** After scoring the Phase 1 keyword detector against the
33 applicable gold-set papers, what does the baseline actually look
like, and are the detector's errors real detector limitations or gold
label problems?

**Method:** Ran `src/phase1_detector.py` (simple rule: disclosed if
any regex pattern matches anywhere in full text, else absent), scored
against hand labels. Manually reviewed all 6 false positives on
out_of_sample_cost_modeling by reading their excerpt context.

**What was found:**

Four of six false positives were genuine detector limitations:
keyword matching cannot distinguish a paper stating it DID something
from a paper stating it explicitly did NOT do something ("transaction
cost modeling would be needed" -- stated as future work, not as a
disclosure) or discussing a concept as its research topic rather than
applying it (a paper about the market-impact literature itself, not
about a strategy that models market impact).

The other two (2503.02680v1, 2602.07085v3) turned out to be genuine
gold-label errors, not detector errors. Investigating them surfaced an
ambiguity in how the checklist's "out-of-sample transaction cost
modeling" element had been interpreted during labeling: it was not
clear, going into the labeling pass, whether slippage modeling ALONE
(without also modeling fees, spread, or market impact) should count as
"disclosed."

**Decision:** Slippage modeling alone counts as disclosed for this
element, since slippage is explicitly one of the checklist's named
cost components (see triage_gold_set.py's regex patterns, which treat
slippage as a first-class match, not a partial one). A paper does not
need to model fees, spread, AND market impact together to be coded
disclosed -- modeling any one of them, applied to actual reported
out-of-sample performance (not just cited as a concept or flagged as
future work), is sufficient.

**Consistency check:** Searched all 23 papers still marked absent on
this element for any mention of "slippage" -- the term that triggered
both relabels. Zero matches. This does not rule out under-labeling via
some other cost-modeling phrasing, but does rule out the specific
inconsistency that prompted this review. No further relabeling applied
on this pass.

**Result: relabeled**
- 2503.02680v1: out_of_sample_cost_modeling absent -> disclosed (derives
  explicit slippage/deviation measure vs. market VWAP, reports OOS
  execution performance in basis points; does not model fees/spread/
  market impact separately -- noted explicitly in the row's notes)
- 2602.07085v3: out_of_sample_cost_modeling absent -> disclosed
  (computes excess returns net of an explicit transaction-cost term)

**Updated Phase 1 baseline scores (33 applicable papers):**

| Element | Precision | Recall | F1 | n positive (gold) |
|---|---|---|---|---|
| Walk-forward validation | 0.857 | 0.462 | 0.600 | 13 |
| Purged/embargoed CV | 0.000 | 0.000 | undefined | 1 |
| Out-of-sample cost modeling | 0.667 | 1.000 | 0.800 | 8 |
| Multiple-testing correction | 0.750 | 0.750 | 0.750 | 4 |
| Multi-window validation | 0.400 | 0.182 | 0.250 | 11 |

**Interpretation:** This is a weak-to-mediocre baseline overall, as
expected for a first-commitment keyword detector -- not something to
be satisfied with, something for Phase 2 to beat. Multi-window
validation is the weakest (regex vocabulary likely too narrow for how
papers actually phrase multi-period testing -- worth investigating
false negatives here the same way cost-modeling false positives were
investigated). Purged/embargoed CV has only 1 true positive in the
whole gold set, making its precision/recall effectively uninformative
at this sample size -- reported as undefined/NaN rather than a
misleadingly precise 0.000, and should not be treated as a real
per-element evaluation on its own.

**Still open:** The four genuine detector false positives (stating
absence, or discussing a concept without applying it) are a structural
limitation of pure keyword matching, not fixable by better keywords --
this is direct motivation for Phase 2 (a classifier that can use
context, not just presence/absence of a term). Multi-window
validation's false negatives (9 of 11 missed) haven't been reviewed
yet the way cost-modeling's false positives were -- worth doing before
finalizing Phase 1 as "done."

**Reproduction:**
    python src/phase1_detector.py
    (after the two label corrections above were applied to
    data/gold_set/gold_set_sample.csv)
