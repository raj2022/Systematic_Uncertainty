# Systematic Uncertainty

**Detecting undisclosed methodological risk in published quantitative finance research.**

[Full project proposal](SYSTEMATIC_UNCERTAINTY_PROPOSAL.md) · [Command reference](COMMANDS.md) · [Open issues](ISSUES.md)

---

## Overview

In physics, a measured result carries two distinct kinds of uncertainty: *statistical* uncertainty, arising from the data itself, and *systematic* uncertainty, arising from the method — miscalibration, bias, an assumption that quietly doesn't hold. Statistical uncertainty is reported constantly in empirical research. Systematic uncertainty, far more consequential and far easier to hide, is often reported barely at all.

This project applies that distinction to quantitative finance research. It builds a tool that reads a paper's methodology section and checks it against five specific, verifiable disclosures:

- Walk-forward validation
- Purged / embargoed cross-validation
- Out-of-sample transaction cost modeling
- Multiple-testing correction
- Multi-window validation

The goal is methodology auditing, not results auditing. No paper's empirical claims are challenged directly — only whether specific, checkable disclosures are present in the text.

This is the second project in a two-project research arc, following [**Track to Trade**](https://github.com/raj2022/Track_to_Trade), which first surfaced this pattern through hand-diagnosed leakage and validation failures in a Kalman/IMM regime-detection model.

## Motivation

Hou, Xue, and Zhang's *Replicating Anomalies* and McLean and Pontiff's *Does Academic Research Destroy Stock Return Predictability?* independently document, across hundreds of published results, that a large share of claimed financial anomalies weaken or vanish out of sample or post-publication. This project asks a narrower, more tractable question upstream of that finding: can the specific warning signs behind that pattern be detected directly from a paper's own methodology text, before anyone attempts a full replication?

## Project status

| Phase | Milestone | Status |
|:---:|---|---|
| 1 | Keyword/phrase baseline detector, scored against a hand-labeled gold set | **Complete.** Gold set: 50 papers (`q-fin.ST`, fixed date window), hand-labeled, 33 applicable. Baseline scored — see results below. |
| 2 | Classifier, evaluated head-to-head against the Phase 1 baseline | Not started — next up |
| 3 | Synthetic ablation test and external replication-failure validation | Not started — contingent on Phase 2 |
| 4 | Corpus-scale disclosure-gap estimate (stretch) | Not scoped |

Category scope for the corpus pull is currently `q-fin.ST` only. `q-fin.CP`, `q-fin.TR`, and `q-fin.PM` are deferred (see [`ISSUES.md`](ISSUES.md)) until later, so the gold set's composition doesn't shift mid-labeling.

Full phase breakdown: [proposal, §6](SYSTEMATIC_UNCERTAINTY_PROPOSAL.md#6-project-phases).

### Phase 1 results

Of the 50 gold-set papers, 17 (34%) were judged not applicable (no empirical/backtested predictive claims — governance frameworks, purely descriptive or theoretical studies). The keyword baseline was scored against the remaining 33 applicable papers:

| Element | Precision | Recall | F1 | n disclosed (gold) |
|---|---:|---:|---:|---:|
| Walk-forward validation | 0.857 | 0.462 | 0.600 | 13 |
| Purged / embargoed CV | 0.000 | 0.000 | n/a (n=1) | 1 |
| Out-of-sample cost modeling | 0.667 | 1.000 | 0.800 | 8 |
| Multiple-testing correction | 0.750 | 0.750 | 0.750 | 4 |
| Multi-window validation | 0.444 | 0.364 | 0.400 | 11 |

A mediocre, uneven baseline, as expected for a first-commitment keyword detector. Its clearest structural limitation — confirmed by manual review of every false positive and false negative — is that keyword matching cannot distinguish a paper *disclosing* something from a paper *stating it was not done*, and struggles to distinguish one validation period described with two dates from genuinely distinct multiple periods. This is the number Phase 2 has to beat, and the specific failure modes found here are the direct motivation for building it. Full investigation: [`notes/004`](notes/004_phase1_baseline_and_cost_modeling_fix.md), [`notes/005`](notes/005_multiwindow_review_and_phase1_final.md).

Separately: among the 33 applicable papers, the **hand-labeled ground truth itself** shows purged/embargoed cross-validation disclosed in only 1 paper (3%) and multiple-testing correction in 4 (12%) — the two rarest disclosures in this sample, consistent with the project's founding hypothesis. See [`notes/003`](notes/003_gold_set_labeling_complete.md) for the full disclosure-rate table and its caveats (small N, single labeler, single category).

## Getting started

```bash
bash setup_env.sh
source .systematic_uncertainty_env/bin/activate
```

Every script, its arguments, and its output are documented in [`COMMANDS.md`](COMMANDS.md).

## Repository structure

```
src/                          Scripts: arXiv corpus pull, triage, detector
data/
├── raw/                      Full pulled arXiv metadata (gitignored, reproducible)
└── gold_set/
    ├── gold_set_sample.csv   Hand-labeled gold set (committed)
    └── excerpts/             Keyword-hit reading aid, per paper (gitignored, regenerable)
notes/                        Derivation log — one entry per substantive decision
results/                      Scored outputs (from Phase 1 onward)
COMMANDS.md                   Command reference
ISSUES.md                     Open items and scope boundaries
```

## Methodological standards

This project is held to the same discipline established in Track to Trade:

1. **Baseline before complexity.** The Phase 1 keyword detector is scored first. Nothing more sophisticated is built until there is a number to beat.
2. **The detector is itself a claim.** Any signal it finds could reflect writing style, paper length, or venue rather than real methodological content. Phase 3's synthetic ablation exists to test this before any result is trusted.
3. **External validation over internal confidence.** Detected risk is checked against independently documented replication failures (Hou/Xue/Zhang, McLean/Pontiff) — a test against something the tool never saw during development.
4. **Negative results are results.** If Phase 2 fails to beat Phase 1, or detected risk does not correlate with known non-replications, that is reported as the finding.
5. **No claim beyond what the method shows.** This tool flags text-level disclosure gaps. It does not claim any specific paper's results are false, and it does not name or rank individual authors or papers as a deliverable.

Full non-goals and a self-audit against Track to Trade's standards: [proposal, §7–8](SYSTEMATIC_UNCERTAINTY_PROPOSAL.md#7-explicit-non-goals).

## Derivation log

Every labeling decision, rejected attempt, and scope call is recorded in [`notes/`](notes/), following the same discipline as Track to Trade. Selected entries:

| Entry | Decision |
|---|---|
| [`001`](notes/001_not_applicable_label_state.md) | Added a fourth gold-set label state, `not_applicable`, distinguishing papers with nothing to disclose from papers that omitted a disclosure |
| [`002`](notes/002_reproducibility_date_window.md) | Pinned the arXiv pull to a fixed submission-date window, since a fixed random seed alone did not make the sample reproducible |
| [`003`](notes/003_gold_set_labeling_complete.md) | Gold-set labeling complete (50 papers); baseline disclosure rates and caveats |
| [`004`](notes/004_phase1_baseline_and_cost_modeling_fix.md) | Phase 1 first scoring pass; found and fixed a gold-label inconsistency (slippage-as-cost-modeling) via false-positive review |
| [`005`](notes/005_multiwindow_review_and_phase1_final.md) | Multi-window false-negative review; a cross-credit rule was tried, found to rest on a false assumption, and reverted; Phase 1 finalized |

## License

Not yet decided.