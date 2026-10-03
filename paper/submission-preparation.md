# Preprints.org submission preparation

Status: prepared locally, not submitted or accepted.

Title: NeuroStreamLab: Hardware-Free Real-Time BCI Development and EEG Replay Robustness

Author: Syed Abdullah Imam

Affiliation: University of North Texas (as supplied by the author)

PDF: paper/main.pdf

Subject suggestion: Engineering, computational neuroengineering / brain computer interfaces. Choose the closest available platform category.

Keywords: EEG, motor imagery, brain computer interface, recorded replay, reproducibility, decoder robustness, BrainFlow

Code: https://github.com/Malanaa/higgings

Paper landing page: https://malanaa.github.io/higgings/publication/

## Abstract extracted from the submitted PDF candidate

Developing brain computer interface software requires acquisition, signal processing, decoding,
timing, and application integration before a useful experiment can be run. Access to EEG
hardware can constrain this engineering work, while offline classification alone does not exercise
a streaming application. We present NeuroStreamLab, an open source local environment that
separates acquisition from timestamped processing and supports BrainFlow synthetic streams,
recorded EEG replay, and an explicit future hardware adapter. A browser console exposes
signals, probabilities, temporal decisions, perturbations, and runtime telemetry. We evaluate
log bandpower logistic regression, common spatial patterns with linear discriminant analysis,
and a CPU-trained EEGNet on held-out imagined left versus right hand trials from PhysioNet
and on cross-session BNCI motor imagery. The exploratory cohort contains 8 participants and
507 test trials. Controlled noise, channel loss, amplitude scaling, drift, and mixed shifts are
applied before trial-local filtering. Clean mean balanced accuracy for CSP plus LDA is 55.9% on
PhysioNet and 73.1% on BNCI. Under the largest tested additive noise, these means are 50.0%
and 50.0%. An unlabeled, causal RMS-alignment reference strategy gives condition-dependent
recovery rather than a universal improvement. Measured inference and software-processing
timings are stored separately from accuracy. All numerical tables and figures are generated from
machine-readable artifacts. The results demonstrate a reproducible development workflow, not
clinical utility or physical acquisition validation. The small cohort, limited electrode set, and
offline trial preprocessing constrain generalization.

## AI disclosure

OpenAI Codex generated software, executed the reported computational experiments and automated checks, and drafted manuscript text under the author's instructions. AI assistance also supported literature searches, figures, and publication packaging. AI systems are not listed as authors. These computational checks do not replace independent scientific review.

## Required author input before submission

The author must personally review and confirm the scientific content and sources. No completed human review is asserted here. Login, contact email, ORCID if available, funding and conflict-of-interest declarations must be supplied by the author. Do not invent these declarations. Review the platform license and copyright agreement before accepting. Public datasets have independent terms and raw recordings are not redistributed. This is a preprint, not a peer-reviewed publication. No DOI has been assigned.

engrXiv was not used because its current AI policy prohibits verbatim generated manuscript paragraphs. Preprints.org requires transparent AI-use disclosure. Neither acceptance nor Google Scholar indexing is guaranteed.
