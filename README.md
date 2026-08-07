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
| 1 | Keyword/phrase baseline detector, scored against a hand-labeled gold set | Gold set pulled (50 papers, `q-fin.ST`, fixed date window) and triaged; hand-labeling in progress |
| 2 | Classifier, evaluated head-to-head against the Phase 1 baseline | Not started — contingent on Phase 1 |
| 3 | Synthetic ablation test and external replication-failure validation | Not started — contingent on Phase 2 |
| 4 | Corpus-scale disclosure-gap estimate (stretch) | Not scoped |

Category scope for the corpus pull is currently `q-fin.ST` only. `q-fin.CP`, `q-fin.TR`, and `q-fin.PM` are deferred (see [`ISSUES.md`](ISSUES.md)) until after Phase 1 is scored, so the gold set's composition doesn't shift mid-labeling.

Full phase breakdown: [proposal, §6](SYSTEMATIC_UNCERTAINTY_PROPOSAL.md#6-project-phases).

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

## License

Not yet decided.
