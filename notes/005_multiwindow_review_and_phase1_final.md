# 005 — Multi-window false-negative review; cross-credit rule tried and reverted; Phase 1 finalized

**Date:** 2026-08-07

**Question:** multi_window_validation had the worst Phase 1 score
(recall 0.182, F1 0.25). Are the 9 false negatives real detector
misses, and can they be fixed without overfitting to this specific
gold set?

**Method:** Reviewed all 9 false-negative papers' notes. All 9 were
genuine detector misses (not label errors) -- the notes describe real,
explicit multi-window validation (distinct folds, rolling steps,
pre/post-COVID periods) that the original narrow regex simply didn't
have vocabulary for.

**First attempt (reverted):** Added a cross-credit rule -- if
walk_forward_validation fires disclosed, credit multi_window_validation
as disclosed too, on the reasoning that walk-forward validation always
touches multiple windows. This raised recall to 0.636 but introduced 9
new false positives. Reviewing those showed the underlying assumption
was wrong: a paper can run genuine walk-forward validation as one
continuous rolling re-estimation process (e.g. 2506.07928v1: daily
re-estimation over 1993-2019) without that constituting "multi-window
validation" under this project's definition, which requires distinct,
separately-identified historical periods, not a single continuous
rolling process. Walk-forward and multi-window are related but not
equivalent under this checklist. The cross-credit rule was removed.

**Second attempt (kept):** Expanded the regex vocabulary directly:
added patterns for numbered folds ("5-fold"), "step" (rolling-CV step
size), pre/post-COVID period language, and "distinct historical
period/window/year" phrasing. An earlier draft of this also included a
loose year-range pattern matching any two years near "train"/"test" --
this was too permissive and fired on single static train/test splits
that mention a start and end year without actually testing multiple
windows (e.g. 2510.01203v1, one chronological split). That pattern was
removed.

**Result:** multi_window_validation: precision 0.444, recall 0.364,
F1 0.40 (up from the original 0.400/0.182/0.25). 5 false positives and
7 false negatives remain.

**Decision: stop tuning multi_window_validation's regex here.** Further
keyword expansion risks overfitting to this specific 33-paper gold set
-- adding a pattern for each remaining false negative's exact phrasing
would inflate Phase 1's apparent performance without reflecting real
generalization, defeating the purpose of having a held-out evaluation
set at all. The remaining errors are reported as Phase 1's honest
limitation, not iterated away.

## Phase 1 baseline: final scores

| Element | Precision | Recall | F1 | n positive (gold) |
|---|---|---|---|---|
| Walk-forward validation | 0.857 | 0.462 | 0.600 | 13 |
| Purged/embargoed CV | 0.000 | 0.000 | undefined (n=1) | 1 |
| Out-of-sample cost modeling | 0.667 | 1.000 | 0.800 | 8 |
| Multiple-testing correction | 0.750 | 0.750 | 0.750 | 4 |
| Multi-window validation | 0.444 | 0.364 | 0.400 | 11 |

**Overall assessment:** a mediocre, uneven baseline, as expected for a
first-commitment keyword detector. Strongest on cost-modeling recall
(catches everything, at the cost of some precision) and
multiple-testing correction (best-balanced, but n=4 is small). Weakest
on purged/embargoed CV (n=1, effectively unscoreable at this sample
size) and multi-window validation (regex fundamentally struggles to
distinguish "multiple distinct periods" from "one period described
with two dates," a genuinely hard NLP problem for keyword matching).

**This is the number Phase 2 has to beat**, per the proposal's Phase 1
gate. The structural failure modes found here (can't distinguish
stated-absence from disclosure; can't distinguish one period from many
without very specific phrasing) are direct motivation for why a
context-aware classifier is worth building, not just a more elaborate
keyword list.

**Reproduction:**
    python src/phase1_detector.py
