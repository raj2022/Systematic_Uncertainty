# 002 — pull_arxiv.py's "seeded" gold set wasn't actually reproducible

**Date:** 2026-08-07

**Question:** Running `pull_arxiv.py --seed 42` twice, hours apart, produced
two different 50-paper gold sets (confirmed: 2607.25459, present in the
first run, was absent from the second run's excerpt files entirely).
Why, if the seed was fixed?

**Method:** Traced the sampling logic. `build_gold_sample()` does seed a
`random.Random(42)` correctly and samples deterministically from
whatever DataFrame it's given. The problem is upstream: `fetch_metadata()`
queried arXiv for "most recent 500 q-fin.ST papers," sorted by submission
date descending, with no date bound. Between the two runs, arXiv had
published new papers, so "most recent 500" was a different 500 papers
each time -- the seed was applied consistently, but to a different input
pool, so the output differed anyway.

**Rejected framing:** Initially assumed the seed itself was broken (e.g.
wrong scope, reset somewhere). It wasn't -- the sampling function is
correct. The bug was treating "most recent N" as a stable identifier when
it isn't; it's a moving window that silently drifts every time the
script runs on a later date.

**Result:** Added an explicit, fixed submission-date window
(`--start-date` / `--end-date`, defaulting to 2020-01-01 through
2026-08-01) to the arXiv query itself. Re-running the script with the
same date window and seed now pulls from the same underlying paper pool
and produces the same gold-set sample, regardless of what's been
published on arXiv since. The default end date is intentionally in the
past relative to now, not "today," so it doesn't silently start moving
again the next time this project is picked up.

**Cost of the bug:** The first gold set (with 2607.25459 in it) was
never hand-labeled, so nothing analytical was lost -- but the venv,
data/, and results/ folders for that run were also lost separately
during an unrelated git repair (see notes/001 area of ISSUES.md), so
this was moot in practice this time. Still a real bug, independent of
that incident, and would have caused a silent, hard-to-notice
reproducibility failure later if not caught now.

**Still open:** The default end date (2026-08-01) will eventually need
deliberately updating if the corpus needs to include more recent papers.
That should be a conscious decision with its own notes/ entry, not an
incidental side effect of re-running the script.

**Reproduction:**
    python src/pull_arxiv.py --max-results 500 --gold-size 50 --seed 42
    (uses DEFAULT_START_DATE / DEFAULT_END_DATE from pull_arxiv.py)
