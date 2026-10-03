# Data leakage audit

- Each epoch has a unique dataset/subject/session/run/event identifier. The runner asserts nonempty disjoint train/test trial IDs and stores IDs with probabilities.
- PhysioNet holds out the full hand-imagery run 12. BNCI holds out session 1test. No fragmented windows from a trial are assigned to multiple splits.
- Each model is within subject. No cross-subject transfer claim is made.
- Zero-phase filters operate on individual epochs, not concatenated train/test data. They are acausal within a trial and disclosed accordingly.
- CSP, classical feature scalers, LDA and logistic regression fit only training epochs.
- EEGNet's scaling and parameter updates use only inner training epochs. Validation chooses the checkpoint using only the outer training split. Validation indices and history are stored.
- Noise scaling is computed from training-only broadband centered RMS. Perturbation arrays are copies, not source-file mutations.
- Unlabeled adaptation accepts no labels. Expanding statistics include the current trial and past trials, and reset for each condition. No future trials.
- All model and scenario hyperparameters are fixed by the hashed YAML before final outcomes. The smoke test used only subject 1. No results-based participant selection.
- Replay loads only held-out trial arrays. Its manifest stores and checks training and test IDs. Ground-truth labels are displayed separately and are used only for session accuracy, not movement or prediction.

Automated checks: tests/test_scientific.py, tests/test_server.py, tests/test_replay_integration.py, and scripts/verify_results_provenance.py. Subject-resampled intervals describe a small cohort and do not make each EEG trial a human replicate.
