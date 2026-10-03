# Known limitations

- No physical EEG hardware or live human acquisition validation. This is not a medical device.
- Recorded replay is not current-user intention. The demo concatenates held-out task epochs and omits original rest intervals.
- Offline and replay trial-end decoders use zero-phase filtering. Continuous filtering is causal, but its accuracy has not been benchmarked here.
- The paper cohort is only five PhysioNet and three BNCI subjects with three central channels. No population superiority or cross-subject generalization.
- EEGNet CPU training is deliberately short, not a competitive hyperparameter search. One seed does not characterize deep training variability.
- RMS adaptation assumes gain-related shift, can remove useful amplitude information and cannot recover missing channels. It has no success guarantee.
- Software timing excludes transport and browser rendering. Loopback scheduling, BrainFlow synthetic timestamps and accelerated replay cannot establish physical-device jitter or user control latency.
- Eight channels and factor-two display sampling limit viewer detail while preserving inference input. The Canvas timing label is a target, not a measured FPS result.
- The scalp panel uses standard MNE label coordinates, not individualized sensor positions. Sparse electrodes are shown without fabricated interpolation. Unknown channel positions are not displayed.
- No LSL or Unity client, rest model or session-load editor. These are optional extensions, not scientific results.
- NEMAR/PhysioNet downloads require internet. Defaults store data locally and do not redistribute EEG. Upstream availability and dataset terms can change.
- The local API is unauthenticated and must remain bound to loopback. Exported sessions are metadata/prediction logs, not complete raw EEG archives.
