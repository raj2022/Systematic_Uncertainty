# Issues

Open items, scope boundaries, and known gaps. Not a bug tracker in the
GitHub-issues sense — this is the plain-text version, checked into the repo,
for things that need a decision or follow-up later. Move resolved items to
the "Resolved" section rather than deleting them, so the decision history
stays visible (same spirit as `notes/`).

---

## Open

### Category scope: only q-fin.ST pulled so far
`q-fin.CP`, `q-fin.TR`, `q-fin.PM` are in the proposal but not yet pulled.
Decide whether to expand before or after Phase 1 baseline is scored —
expanding later risks changing the gold set's composition after labeling
has started, which is worth avoiding if possible.

### ar5iv coverage is incomplete
Some papers, especially very recent submissions, have no ar5iv HTML
rendering. `triage_gold_set.py` flags these but doesn't handle them —
falls back to a manual PDF read. Track how many of the 50 hit this; if
it's a large fraction, worth a PDF-text-extraction fallback instead of
relying on ar5iv alone.

### Regex patterns in triage_gold_set.py are unvalidated
The keyword patterns per checklist element were written by hand, not
tested against known papers with confirmed disclosures. Before trusting
the triage output at scale, spot-check the first several papers' excerpts
against a full manual read to confirm the patterns aren't missing common
phrasings.

### Full-text vs. metadata-only pull
`pull_arxiv.py` only pulls title/abstract, not full text. Full text is
fetched separately and only for the gold set via `triage_gold_set.py`
(ar5iv). If Phase 1's keyword detector needs to run on the full raw
corpus (not just the gold set), a full-text pull for all 500 papers will
be needed — currently out of scope.

---

## Resolved

### Labeling schema was missing a not_applicable state
Originally tri-state (disclosed/absent/ambiguous). Manual read of a
5/5-blank paper (2608.02311v1) showed it was a governance-framework
paper with no backtest content at all -- correctly 0/5 not because it
omitted disclosures but because the checklist doesn't apply to it.
Added a fourth state, `not_applicable`. See `notes/001_not_applicable_label_state.md`.
Still open: a consistent rule for what counts as "reports empirical
results," not just per-paper judgment -- revisit after more labeling.

### pull_arxiv.py's seed wasn't actually reproducible
"Most recent 500 papers" silently drifts every time the script runs on
a later date, even with a fixed --seed, because the seed only controls
sampling *from* the pulled pool, not what that pool contains. Fixed by
pinning an explicit submission-date window. See
`notes/002_reproducibility_date_window.md`. Still open: the default
end date will need a deliberate, logged update eventually.

## Open (added after Phase 1)

### Fine-tuned transformer for Phase 2 -- deferred
Considered building both an LLM-extraction classifier and a fine-tuned
transformer for Phase 2, to compare head-to-head. Deferred: a
fine-tuned transformer needs far more labeled examples than the
current 33-50 applicable papers to learn 5 separate classification
tasks without just memorizing the training set, and pursuing both in
parallel splits effort before either is known to beat Phase 1. Revisit
only if LLM-extraction clearly beats Phase 1 (worth a second comparison
point) or clearly doesn't (worth trying a different approach) -- and
if pursued, needs its own labeled-data expansion plan, not an
incidental side effect of "we have a bit more time."
