# Commands

Reference for every script in this repo: what it does, how to run it, what it produces.

---

## Environment setup

```bash
bash setup_env.sh
source .systematic_uncertainty_env/bin/activate
```

Creates the virtual environment and installs everything in `requirements.txt`.
Run once per machine. Reactivate with the `source` line in every new terminal session.

If `requirements.txt` changes later:

```bash
pip install -r requirements.txt
```

---

## `src/pull_arxiv.py`

Pulls paper metadata from arXiv for `q-fin.ST` (other q-fin categories are
an open item, see `ISSUES.md`). Writes the full pulled set to
`data/raw/qfin_st_metadata.csv`, and a random sample to
`data/gold_set/gold_set_sample.csv` with empty checklist columns ready for
hand-labeling.

```bash
python src/pull_arxiv.py --max-results 500 --gold-size 50
```

**Flags:**
- `--max-results` (default 500): how many papers to pull from `q-fin.ST`
- `--gold-size` (default 50): how many of those to sample for the gold set
- `--seed` (default 42): random seed for the gold-set sample (kept fixed for reproducibility)

**Output:**
- `data/raw/qfin_st_metadata.csv` — gitignored, full pulled metadata
- `data/gold_set/gold_set_sample.csv` — committed, the file you hand-label in

---

## `src/triage_gold_set.py`

For each paper in the gold set, fetches full text via ar5iv and searches
for phrasings tied to each checklist element. Outputs one markdown file
per paper with matched excerpts, so hand-labeling means reading ~5–15
flagged sentences instead of the whole paper. Does not label anything
itself — the disclosed/absent/ambiguous call is still made by hand in
`gold_set_sample.csv`.

```bash
python src/triage_gold_set.py
```

**Requires:** `data/gold_set/gold_set_sample.csv` to already exist (run `pull_arxiv.py` first).

**Output:**
- `data/gold_set/excerpts/<arxiv_id>.md` — one file per paper
- Console list of any papers with no ar5iv rendering (need a manual PDF read instead)

---

## Git

```bash
git add <files>
git commit -m "message"
git push origin main
```

Standard workflow, no project-specific wrapper yet.

---

*Add new scripts here as they're written — Phase 1 detector, Phase 2 classifier, Phase 3 ablation/validation scripts, etc.*
