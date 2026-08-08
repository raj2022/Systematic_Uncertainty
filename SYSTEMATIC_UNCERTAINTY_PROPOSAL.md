# Systematic Uncertainty
### Detecting Undisclosed Methodological Risk in Published Quantitative Finance Research
**Project proposal**

---

## 1. One-line thesis

In physics, a result has two kinds of uncertainty: statistical, from the data, and systematic, from the method itself, miscalibration, bias, an assumption that doesn't hold. Published quantitative finance research reports the first kind constantly and the second kind almost never. This project builds a tool that reads a paper's methodology section and flags exactly the category of undisclosed systematic risk this candidate has now personally diagnosed by hand three times, missing walk-forward validation, single-window results, vague or absent leakage controls, and asks a harder second question: can that detector itself be trusted, or does it need the same identifiability scrutiny as everything else in this line of work.

This is a methodology-auditing project, not an accusation engine. No paper's empirical results are challenged directly; only whether specific, checkable disclosures are present in the text.

---

## 2. Motivation: systematizing something already proven by hand

This project exists because of a pattern, not a hunch.

**MLPF:** aggregate accuracy concealed a domain-specific failure invisible without targeted validation.

**Track to Trade, Phase 2:** a label-construction leakage artifact evaded two constructed nulls before a third, properly controlled one caught it, then had to be independently replicated on a second window before the earlier residual could be trusted as noise rather than a real, unexplained bias.

**Track to Trade, Phase 4:** nine architectures were tested honestly against a simple baseline and all nine lost, a negative result reported as the finding rather than discarded.

Each of these was a manual, one-paper-at-a-time act of exactly the kind of scrutiny the finance literature's own replication crisis says is systematically missing at scale. Hou, Xue, and Zhang's *Replicating Anomalies* and McLean and Pontiff's *Does Academic Research Destroy Stock Return Predictability?* both document, across hundreds of published results, that a large share of claimed anomalies weaken or disappear out of sample or post-publication. That is the field-level version of the exact failure this candidate has now caught by hand three times in one project. This project asks whether the specific, legible warning signs, the kind that were personally hard-won in Track to Trade, can be detected directly from a paper's own text, before anyone attempts to replicate the result at all.

---

## 3. Core research question

> Can a small set of specific, disclosed-or-not methodological elements, purged or embargoed cross-validation, walk-forward evaluation, out-of-sample transaction cost modeling, multiple-testing correction, single-window versus multi-window validation, be reliably detected from a paper's methods text? And can that detector be validated against something other than its own confidence, without falling into the same trap the detector exists to catch: a plausible-looking signal that turns out to be an artifact of superficial style rather than real methodological content?

Secondary question: does detected disclosure risk correlate with independently known replication failures in the literature, a real, external check on whether this measures something true rather than something merely self-consistent.

---

## 4. Principles carried forward, stated explicitly

- **Baseline before complexity.** A simple keyword and phrase detector comes first. Anything more sophisticated has to beat it on a held-out labeled set before it's trusted, the same standard nine architectures failed to clear in Track to Trade Phase 4.
- **The detector is itself a claim that needs its own null.** A model that scores papers on disclosure risk could just as easily be picking up field, venue, paper length, or writing style as a stand-in for real methodological content, structurally the same risk as a null-label construction that accidentally encodes real structure instead of nothing. This gets a control before any result is trusted, an ablation where methodology sections are edited to add or remove specific disclosures with everything else held fixed, testing whether the detector responds to the actual content change.
- **External validation over internal confidence.** A detector that agrees with itself proves nothing. Checking detected risk against papers with independently documented replication failures is the equivalent of Track to Trade's second-window confirmation, a check against something the tool didn't see during development.
- **Negative results are results.** If the sophisticated classifier doesn't beat the keyword baseline, or detected risk doesn't correlate with known replication failures, that is reported as the finding, not iterated on until it looks better.
- **No claim beyond what's actually shown.** This project flags disclosure gaps in text. It does not, and cannot, verify a paper's code, data, or actual empirical correctness. That boundary gets stated explicitly rather than blurred.

---

## 5. Data

- **Primary corpus:** arXiv `q-fin` papers (quantitative finance), pulled via the arXiv API, focused on categories most likely to contain backtested or predictive claims (`q-fin.ST`, `q-fin.CP`, `q-fin.TR`, `q-fin.PM`). Public, free, no API key, directly comparable in spirit to the Binance data pipeline already built.
- **Hand-labeled gold set:** a few dozen papers read and scored personally against the exact checklist Track to Trade's own Section 8 audit already used, walk-forward validation, leakage controls, cost modeling, multi-window testing, this becomes the first real ground truth, not an assumed one.
- **External validation set:** papers or claimed anomalies with documented non-replication in *Replicating Anomalies* and similar follow-up literature, used as an independent, previously-unseen check rather than something the detector was tuned against.
- **Synthetic ablation set:** methodology sections from known well-documented papers, edited to add or strip specific disclosures with everything else held constant, the detector's version of a controlled experiment rather than only observational text.

---

## 6. Project phases

### Phase 1 (first commitment): keyword and phrase baseline

- Build a simple, interpretable detector: regex and phrase matching for the specific disclosure elements (walk-forward, purged/embargoed, out-of-sample, transaction cost, multiple testing correction, look-ahead).
- Score the hand-labeled gold set. This is the number everything else has to beat.

### Phase 2 (only if Phase 1 gives something worth improving on): a real classifier

- Fine-tuned lightweight transformer or structured LLM extraction, prompted against the same checklist criteria rather than a vague "is this paper rigorous" question.
- Head-to-head against the Phase 1 baseline on the same held-out gold set. Complexity has to earn its place, same standard as Track to Trade Phase 4.

### Phase 3 (the centerpiece): does the detector measure something real

- Synthetic ablation test: does detected risk change correctly when disclosures are added or removed from otherwise-identical text.
- External check: does detected risk correlate with independently documented replication failures.
- This phase is not optional polish, it is the part that determines whether Phases 1 and 2 mean anything at all.

### Phase 4 (stretch, gated on Phase 3 holding up)

- Apply at scale across the full pulled corpus, report an honestly bounded, precision-and-recall-qualified estimate of how common specific disclosure gaps are, not a headline "X% of papers are wrong" claim the method can't support.

---

## 7. Explicit non-goals

- No claim that any specific, named paper's results are false, fraudulent, or invalid. Only that specific text-level disclosures are present or absent.
- No public ranking or naming of individual authors or papers as a deliverable; any illustrative examples used in the write-up are chosen for their methodological pattern, not to single anyone out.
- No claim that text-based detection substitutes for actual code or data replication.
- No claim of a complete or exhaustive checklist; the elements checked are the ones this candidate has personally encountered failure modes for, stated as a scope boundary, not hidden as one.

---

## 8. Self-audit against the prior project's standards

| Principle from Track to Trade | Carried forward how |
|---|---|
| Baseline before complexity | Phase 1's entire purpose |
| The null/control needs its own verification | Phase 3's synthetic ablation |
| External replication over internal confidence | Phase 3's check against documented non-replications |
| Report negative results honestly | Explicit non-goal; Phase 2 only proceeds if it beats Phase 1 |
| Don't overclaim past what the method shows | Section 7, stated before any results exist |

---

## 9. Derivation log

Not yet started. Same format as `Track_to_Trade/notes/`: question, method, rejected attempts, result, reproduction command.

---

## 10. Deliverables

- New public GitHub repository, `Systematic_Uncertainty` or similar.
- `notes/`: derivation log for every labeling and validation decision.
- The hand-labeled gold set itself, released alongside the code, since it's a real, reusable contribution independent of the detector's eventual performance.
- A short technical note after Phase 3 regardless of outcome.

## 11. Timeline
 
| Phase | Milestone | Status |
|---|---|---|
| 1 | Keyword baseline, scored against a hand-labeled gold set | **Complete.** 50-paper gold set (`q-fin.ST`, fixed date window), hand-labeled; 33/50 applicable. Baseline F1 ranged 0.40-0.80 across elements, weakest on multi-window validation and purged/embargoed CV (n=1, effectively unscoreable at this sample size). See `notes/003`-`005`. |
| 2 | Classifier, head-to-head against Phase 1 | Not started, contingent — Phase 1 gave real signal to beat (see above), so this proceeds |
| 3 | Synthetic ablation and external replication-failure check | Not started, contingent |
| 4 | Corpus-scale estimate, stretch | Not scoped |

## 12. What a 45-minute interview conversation looks like

- *"Isn't this just sentiment analysis for finance papers?"* → no, it targets specific, checkable methodological disclosures, not tone or opinion, and it's validated against real replication-failure outcomes, not self-reported confidence.
- *"How do you know the detector isn't just picking up writing style?"* → that's exactly what Phase 3's synthetic ablation is built to rule out.
- *"What would make you distrust your own tool?"* → if it doesn't beat the keyword baseline, or if detected risk doesn't correlate with documented non-replications, both are stated up front as the conditions that would kill the result.
- *"Why does a physicist think they can evaluate finance papers?"* → the checklist comes directly from three specific failure modes personally diagnosed and fixed in prior work, not from finance theory.
- *"How does this connect to your other work?"* → it's the same aggregate-metric-hides-a-real-problem pattern, applied to the field's own literature instead of to one model.
