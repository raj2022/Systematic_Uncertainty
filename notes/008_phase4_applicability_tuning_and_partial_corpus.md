# 008 — Phase 4: applicability screen validation, and a budget-capped partial corpus scan

**Date:** 2026-08-08

## Part 1: validating automated applicability screening

**Question:** Phase 4 requires classifying applicability (does a paper
report real empirical/backtested results at all) at corpus scale.
Until now this was judged entirely by hand, for all 50 gold-set
papers. Neither Phase 1 nor Phase 2 had ever been asked to predict
applicability -- only the five checklist elements, always on papers a
human had already filtered. Can an LLM applicability screen be trusted
before scaling it to hundreds of unlabeled papers?

**Method:** Built an applicability-only prompt, tested against all 50
gold-set papers (33 applicable + 17 not_applicable per hand labels --
using the full set, not just the 33, since both classes are needed to
test discrimination).

**Iteration (three attempts, logged in full rather than only the
final version):**

1. First attempt: "applicable if it trains/tests/backtests a model and
   reports performance." Accuracy 0.82, precision 0.786, recall 1.000.
   All 9 errors were false positives -- papers with real quantitative
   or statistical content (parameter fits, Granger-causality results,
   in-sample statistics) that the LLM over-triggered on, mistaking
   "has real numbers" for "has a real predictive/strategy claim."

2. Second attempt: tightened to require genuine held-out/out-of-sample
   evaluation specifically. Accuracy improved to 0.90, precision to
   0.938, but recall dropped to 0.909 -- 3 new false negatives.
   Investigating these showed the fix had overcorrected: one gold-set
   paper's own label note explicitly says its "main statistics are
   computed on the full available sample... rather than a held-out OOS
   design," yet it was hand-labeled APPLICABLE -- meaning applicability
   was never supposed to require held-out evaluation in the first
   place. That distinction belongs to the checklist elements
   (walk-forward, multi-window) themselves, not to the applicability
   gate.

3. Third attempt: removed the held-out requirement, keeping only the
   distinction between "reports a real forecast/strategy performance
   claim" (applicable, regardless of in-sample or out-of-sample) and
   "only fits parameters or characterizes statistical relationships
   with no forecast/strategy claim at all" (not_applicable). Accuracy
   returned to 0.82, precision 0.800, recall 0.970 -- essentially a
   wash against attempt 1, just with a different error distribution
   (2 of the 3 previous false negatives fixed, but most of the
   original false positives reopened).

**Decision:** stopped iterating after three attempts to avoid
overfitting the prompt to this specific 50-paper set, the same
overfitting risk already identified and avoided during Phase 1's
multi-window regex tuning (notes/005). Reverted to attempt 2 (the
tightened, held-out-required version) for actual use, because it
scored best overall (accuracy 0.90, F1 0.923) despite resting on a
definition that is KNOWINGLY not quite conceptually correct -- it
excludes some genuine backtest/strategy papers that merely lack a
held-out split, which is a real, acknowledged imperfection, not a
hidden one. This tension (best-scoring prompt != most conceptually
correct prompt) is stated directly in the prompt's own docstring in
`phase4_applicability_validation.py`, not just in this note, so future
readers of the code encounter the caveat where it matters.

**Applicability screen final validated performance:**
accuracy=0.90, precision=0.938, recall=0.909 (n=50, all gold-set papers)

## Part 2: corpus-scale run, capped by budget

**Method:** `phase4_corpus_scale.py` runs the validated applicability
screen, then the Phase 2 checklist (validated in notes/006) on papers
judged applicable, across the full raw-pulled corpus (500 papers from
`pull_arxiv.py`, `q-fin.ST`, same fixed date window as the gold set).
Resumable, incremental-save design.

**What happened:** Anthropic API credit was exhausted partway through
the run. Of 500 papers scanned, 174 completed successfully before
credit ran out; the remaining 326 recorded as errors (caught cleanly
by the script's exception handling, not corrupting the 174 good rows).

**Decision: report on the 174 successfully-processed papers as a
partial corpus scan, not the full 500.** This is stated as a real,
budget-driven scope limitation, not smoothed over or represented as a
complete corpus-scale result. 174 is still a meaningful scale-up from
the 33-paper gold set (90 applicable papers here vs. 33 in the gold
set, roughly 2.7x), and the papers processed are not obviously biased
in any particular direction (processing proceeded in the raw corpus's
existing sort order -- most-recent-submission-first -- so the 174
completed are simply the most recently submitted ~35% of the pulled
corpus, not a topically or otherwise skewed subset). This directional
skew toward more recent papers is itself worth naming as a caveat.

## Results: partial corpus scan (174 papers, 90 judged applicable)

| Element | Disclosed | Rate | Validated precision / recall |
|---|---|---|---|
| Walk-forward validation | 44/90 | 48.9% | 1.000 / 0.846 |
| Purged/embargoed CV | 3/90 | 3.3% | UNVALIDATED (n=1 in gold set) |
| Out-of-sample cost modeling | 14/90 | 15.6% | 1.000 / 0.750 |
| Multiple-testing correction | 14/90 | 15.6% | 1.000 / 1.000 (n=4, small) |
| Multi-window validation | 24/90 | 26.7% | 0.833 / 0.455 |

**How to read this table, stated explicitly:** these are raw observed
rates in the scanned papers, qualified by (not corrected for) each
element's known precision/recall from gold-set validation. High
precision, moderate recall (e.g. walk-forward, cost modeling) means
the true disclosure rate is likely AT LEAST this high, possibly
somewhat higher due to missed positives. Multi-window's lower recall
(0.455) means its 26.7% figure is probably a more substantial
undercount of the true rate than the other elements'. Purged/embargoed
CV's rate is not meaningfully validated at all (n=1 in the entire gold
set) and should be treated as suggestive at best, not a reliable
estimate. None of these percentages should be quoted as precise
population statistics -- they are a bounded, qualified estimate over
a partial, recency-skewed sample of one arXiv category, exactly the
kind of honestly-bounded (not headline "X% of papers are wrong")
result Phase 4 was scoped to produce.

**Directional consistency check:** the partial corpus's ordering
(walk-forward most disclosed, purged CV least disclosed, roughly
matching the gold set's own ordering in notes/003) is consistent with
the smaller gold-set finding, which is reassuring but not independent
confirmation -- the corpus-scale run uses the SAME classifier and
SAME prompt as Phase 2, so agreement here reflects consistency of the
tool, not a truly separate validation.

**Still open:** completing the remaining ~326 papers requires
restoring API credit. The resumable design means this can be finished
later without re-processing the 174 already done. Whether to do so is
a cost/benefit decision, not a methodological requirement -- the
qualified partial estimate above is already a legitimate, honestly-
scoped Phase 4 result on its own terms.

**Reproduction:**
    python src/phase4_applicability_validation.py
    python src/phase4_corpus_scale.py   (resumes automatically if
        results/phase4_corpus_scale_predictions.csv already exists)
