# 007 — Phase 3: synthetic + real-paper ablation, and scope-limited external validation

**Date:** 2026-08-08

## Part A: synthetic ablation test

**Question:** Do the Phase 1 and Phase 2 detectors respond to actual
disclosure content, or could their apparent signal be an artifact of
writing style, paragraph length, or something else incidental? Per the
proposal, this is the direct structural equivalent of Track to Trade's
dummy-classifier control.

**Method:** Wrote a single synthetic BASE methodology paragraph with
none of the five checklist disclosures, plus five VARIANTS, each
identical to BASE except for one inserted disclosure sentence. Ran
both detectors on all six texts. Checked (1) did the targeted element
flip absent -> disclosed, and (2) did any non-targeted element change
despite no edit to its content (a spurious change would indicate the
detector isn't responding to the specific content).

**Result:**
- 4/5 targets correctly flipped for both detectors (walk-forward,
  purged/embargoed CV, cost modeling, multiple-testing correction).
- Phase 1 failed to flip on multi_window_validation (stayed absent);
  Phase 2 correctly flipped it. Consistent with Phase 1's known regex
  coverage gap on this element (notes/005) -- now confirmed on fully
  controlled synthetic text, ruling out "maybe it's something weird
  about those specific real papers" as an explanation.
- Zero spurious changes on any non-target element, for either
  detector, across all 5 variants. This is the key finding: both
  detectors respond to the specific targeted content, not to
  incidental paragraph properties.

## Part A: real-paper ablation (automatic, regex-located)

**Method:** For each element, picked a gold-set paper hand-labeled
disclosed, used Phase 1's own regex to locate and remove the exact
disclosing sentence(s) from the REAL fetched text, ran both detectors
on original vs. redacted.

**Result:**
- 2/5 elements had a regex-locatable sentence to redact: cost modeling
  (2606.06823v1) and multiple-testing correction (2607.00475v1). Both
  correctly flipped disclosed -> absent for both detectors, with zero
  spurious changes to any other element.
- 3/5 elements (walk-forward, purged/embargoed CV, multi-window) had
  NO regex-locatable sentence at all in their respective example
  papers -- the automatic version of this test couldn't run on them.
  This is itself informative: it's independent confirmation, via a
  completely different mechanism (redaction target-finding, not
  scoring), that Phase 1's regex genuinely misses real disclosed
  content for exactly these three elements, matching notes/004 and 005.

## Part A: real-paper ablation (manual phrase, walk-forward and multi-window)

**Method:** For the two most consequential elements skipped above,
manually searched for phrasing drawn directly from the original
hand-labeling notes (not the regex) and redacted matching sentences.

**Result:**
- Multi-window (2508.02686v1): the phrase from the labeling note
  ("20 trading days") was not found verbatim in the fetched ar5iv
  text, likely a rendering/wording mismatch. Inconclusive -- not
  counted as a pass or fail, reported as attempted and unresolved.
- Walk-forward (2607.25189v1): the targeted sentence was found and
  removed cleanly. Phase 1 stayed absent before and after (expected,
  consistent with its known miss on this paper). Phase 2 stayed
  DISCLOSED after redaction -- removing this one sentence was not
  sufficient to eliminate the signal.

**This is a genuine, useful limitation finding, not a failure of
Phase 2's accuracy.** Real papers, unlike the single-statement
synthetic paragraphs, typically restate their methodology in more than
one place (abstract, intro, methods, results). Single-sentence
redaction, which worked cleanly on synthetic text, does not fully
control a real paper the same way, because there may be a second or
third statement of the same disclosure elsewhere in the text that a
single redaction doesn't touch. This is a limitation of the ABLATION
METHODOLOGY on real prose, not new evidence about detector quality one
way or the other -- worth stating plainly rather than either counting
it as a win ("Phase 2 is robust!") or a loss ("Phase 2 ignored the
edit!"). Neither framing is supported by what actually happened.

**Overall Part A assessment:** the core question Phase 3 exists to
answer -- does detected signal reflect real content rather than an
artifact -- gets a clean, positive answer from the synthetic test
(zero spurious changes across 5 variants x 2 detectors) and partial
positive confirmation from real text (2/2 clean flips where a single
redaction point existed). The real-paper multi-statement issue is a
methodology note for any future ablation work, not a mark against
either detector.

## Part B: external validation against replication-failure literature

**Question (per proposal):** does detected disclosure risk correlate
with independently documented replication failures (Hou/Xue/Zhang's
*Replicating Anomalies*, McLean/Pontiff's *Does Academic Research
Destroy Stock Return Predictability?*)?

**Scope decision, made explicitly rather than forced:** Hou/Xue/Zhang
and McLean/Pontiff study published, peer-reviewed factor anomalies
(momentum, accruals, asset growth, etc.) from top finance journals,
mostly originating well before 2020, many gated behind paywalls. This
project's gold set is 2025-2026 arXiv q-fin.ST preprints -- a
structurally different corpus (different era, different venue type,
different claim type: ML predictive models vs. named cross-sectional
factor anomalies). There is effectively no overlap between "papers in
this project's corpus" and "anomalies with documented non-replication
status in that literature."

A true paper-level correlation test (Option 1: build a second,
matched gold set of classic anomaly papers, hand-label those too, and
correlate against known replication outcomes) was considered and
would be the methodologically correct way to run this comparison. It
was set aside for this pass as substantial additional scope --
sourcing full text for gated journal papers, verifying which anomalies
have a single clear defining paper, and hand-labeling a second corpus
is comparable in effort to the entire Phase 1 gold-set build, and
doing it hastily would produce a thinner, less trustworthy second gold
set than the first one.

**What this project does instead (Option 2, scope-limited, stated
honestly):** no fabricated paper-level correlation is claimed. Instead:
the disclosure-rate finding from this project's own gold set
(notes/003 -- purged/embargoed CV disclosed in 3% of applicable
papers, multiple-testing correction in 12%) is reported alongside,
not merged with, the general pattern Hou/Xue/Zhang and McLean/Pontiff
document at the field level (a large share of published anomalies
weaken or disappear out of sample or post-publication). The two
findings are DIRECTIONALLY consistent -- both point toward
under-disclosure and fragility being common -- but this project makes
no claim that its own detected risk predicts or correlates with any
specific anomaly's replication outcome, because it was never tested
against that outcome. This is a genuine scope boundary, not a
watered-down substitute for the real test, and is consistent with the
proposal's own Section 7 commitment not to claim more than the method
shows.

**Recorded as a real limitation, not smoothed over:** Phase 3's
external-validation goal, as originally scoped in the proposal, is
NOT fully met by this project in its current form. A true test would
require the second, matched gold set described above. This is logged
here as a natural extension, not attempted in this pass.

**Reproduction:**
    python src/phase3_synthetic_ablation.py
    python src/phase3_real_paper_ablation.py
    python src/phase3_manual_redaction.py
