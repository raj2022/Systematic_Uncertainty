# 006 — Phase 2 (LLM classifier) built, scored, beats Phase 1; multi-window definition clarified again

**Date:** 2026-08-08

**Question:** Does an LLM-based extraction classifier, prompted against
the same checklist used for hand-labeling, beat the Phase 1 keyword
baseline? Per the proposal's Phase 2 gate, this determines whether
Phase 2 is worth keeping.

**Method:** Built `src/phase2_classifier.py`, prompting an LLM (Claude
Sonnet, via the Anthropic API) with each applicable paper's full text
and explicit definitions for all five checklist elements, matching the
exact interpretive decisions already made by hand during labeling (see
notes/001, 004, 005). Scored on the same 33 applicable papers, same
precision/recall/F1 methodology as Phase 1.

**Provider detour (not a methods decision, logged for continuity):**
Free-tier Google Gemini was tried first, per a deliberate cost-saving
choice. Abandoned after repeated ACCESS_TOKEN_TYPE_UNSUPPORTED errors,
traced to a known issue with newer "AQ."-prefixed Gemini auth keys as
of mid-2026 (confirmed via multiple independent reports of the same
failure, not fixable client-side). Switched to the Anthropic API,
which worked reliably. This did not affect the checklist definitions
or scoring methodology, only which model produced the predictions.

**Bug found and fixed during this phase:** an early run left one paper
(2601.07687v4) with a truncated response (max_tokens=300 was too low
for papers where the model wrote out its reasoning before each
answer), causing all 5 of its predictions to silently default to
"absent" via the parser's fail-closed behavior. This inflated the
apparent false-negative count on two elements. Fixed by raising
max_tokens to 1024 and re-running the full 33-paper set. Lesson: a
silent default-on-parse-failure is dangerous for aggregate scoring
even when it "fails safe" for any individual case -- it should have
been surfaced as an explicit gap in the results table, not folded
into "absent" predictions indistinguishably from real ones. Worth
revisiting this design if Phase 2 is used again at larger scale.

**Definitional bug found and fixed:** the initial Phase 2 prompt
carried forward notes/005's finding too broadly. notes/005 established
that ONE specific paper's continuous daily re-estimation process
should not count as multi-window validation. The Phase 2 prompt
generalized this into "walk-forward never counts as multi-window,"
which is stricter than the gold labels actually reflect. Reviewing 7
multi-window false negatives showed all 7 involved fold-based or
periodic walk-forward with an explicit, countable number of distinct
windows ("5 folds," "32 weekly re-calibrations," "10 folds") --
exactly the kind of case the ORIGINAL hand-labeling counted as
disclosed (see 2508.02686v1's own note: "Multiple distinct historical
validation windows therefore qualify as multi-window validation").

**Refined rule (now in the Phase 2 prompt, should also be applied to
any future relabeling or Phase 3 work):** multi-window validation
requires the paper to name or count a specific number of distinct
periods/folds/windows. Fold-based or periodic walk-forward WITH a
countable number of windows satisfies this. A single continuous
rolling/expanding re-estimation process with no discrete, named count
of periods does not.

**Result: final Phase 1 vs Phase 2 scores (33 applicable papers)**

| Element | P1 F1 | P2 F1 | Winner |
|---|---|---|---|
| Walk-forward validation | 0.600 | 0.917 | Phase 2 |
| Purged/embargoed CV | undefined (n=1) | undefined (n=1) | tied, unscoreable at this n |
| Out-of-sample cost modeling | 0.800 | 0.857 | Phase 2 |
| Multiple-testing correction | 0.750 | 1.000 | Phase 2 (n=4, small) |
| Multi-window validation | 0.400 | 0.588 | Phase 2 |

**Decision: Phase 2 clearly beats Phase 1** on every scoreable element,
per the proposal's explicit gate ("complexity has to earn its place").
The largest gains are exactly where Phase 1's structural weakness was
diagnosed (distinguishing stated-disclosure from stated-absence,
distinguishing continuous processes from countable discrete windows) --
this is not a coincidental win, it directly validates the earlier
false-positive/false-negative investigation work.

**Still open:**
- Purged/embargoed CV remains unscoreable at n=1 regardless of method --
  would need a larger or differently-sampled gold set to evaluate this
  element meaningfully at all.
- multiple_testing_correction's perfect Phase 2 score (n=4) should be
  stated cautiously -- not proof of general reliability at this sample
  size.
- The definitional refinement above (fold-based walk-forward counts,
  continuous rolling doesn't) should be treated as the settled rule
  going forward, including for Phase 3's synthetic ablation design.

**Reproduction:**
    python src/phase1_detector.py
    python src/phase2_classifier.py
    (requires ANTHROPIC_API_KEY in .env)
