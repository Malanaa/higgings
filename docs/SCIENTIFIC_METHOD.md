# Scientific method

The frozen paper_v1 YAML is the source of experimental choices. The freeze manifest stores its SHA-256 before the final cohort run. A subject-1 smoke run checked API compatibility and runtime. Subjects 1-5 from PhysioNet and 1-3 from BNCI are a feasibility cohort, not a performance-selected sample.

PhysioNet: MNE EEGBCI imagined hand runs 4 and 8 train, run 12 test. Events T1/T2 map to left/right hand. No executed movement, rest baseline or hands/feet runs. BNCI2014_001: MOABB LeftRightImagery with fmin/fmax None for raw epochs, first session train and second session test. Default artifact handling is retained, not tuned after inspecting accuracy. Original task-event conventions apply to each dataset, so intervals are event-relative and not guaranteed identical neurophysiological task phases.

Each complete epoch is [0.5,3.5) seconds, C3/Cz/C4 in fixed order, microvolts. Sample rates are retained at 160 and 250 Hz. Perturbation is applied before fourth-order 8-30 Hz zero-phase Butterworth filtering. Mean removal is trial-local. No additional notch, average reference or resampling. Offline processing uses future samples within the same complete trial and is not a continuous causal accuracy benchmark.

CSP covariance, feature normalization and classifier fitting use training only. Bandpower means integrated power in the configured filtered band, not independent subbands. EEGNet uses CPU Adam, learning rate .001, batches 16, at most 30 epochs, patience 8, and a training-only stratified 20% validation split. Scaling is fitted only on the inner training subset. Seeds are 42. No model search against the held-out set.

Noise SD is .5, 1 or 2 times centered training-only raw channel RMS. Fixed loss zeros C3, then C3 and C4. Drift amplitude is 2 training RMS at .2 Hz. Gain is 2. Mixed combines noise 1 and gain 2. Perturbations model engineering stressors, not clinical artifacts or probabilities of electrode failure. Gaussian noise is broadband before filtering.

Unlabeled RMS alignment uses filtered training RMS and expanding test RMS, including the current complete trial but no future trial or labels. Gain correction is clipped [.25,4]. It resets for each condition/model/subject and preserves chronological order. It may harm useful amplitude structure. It is a baseline, not a novel algorithm.

The statistical unit is a subject. Primary means and descriptive 95% percentile intervals use 2000 subject bootstrap samples. Paired adaptation differences resample subject differences. No formal significance tests, so no multiplicity-adjusted p-values are manufactured. Metrics include accuracy, balanced accuracy, ROC AUC, F1, Brier score and confusion. Figures retain full [0,1] balanced-accuracy axes.

Latency uses perf_counter_ns, ten warmups and 100 batch-size-one inference calls per trained model, one CPU thread for EEGNet. Figures/tables do not label those times end-to-end latency. The separate streaming profile measures worker processing on real synthetic BrainFlow and accelerated held-out replay, excluding transport and browser. The replay profile median is dominated by non-prediction chunks. No hardware timing is claimed.
