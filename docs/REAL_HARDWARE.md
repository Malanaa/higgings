# Future hardware acquisition

No physical board was tested. The BrainFlowSource adapter is designed around BrainFlow-compatible acquisition. It does not guarantee every BrainFlow device behaves identically.

Explicit Python example:

```python
from neurostreamlab.sources.brainflow import BrainFlowSource
source = BrainFlowSource(board_id=YOUR_BOARD_ID,
                         parameters=YOUR_EXPLICIT_PARAMETERS,
                         allow_hardware=True)
try:
    source.connect()
    source.start()
    chunk = source.read()
finally:
    source.close()
```

Set board-specific parameters after consulting the official BrainFlow documentation. No guessed port, credentials or silent connection is supplied. The local UI cannot initiate physical acquisition. All downstream data is in microvolts, with source metadata carrying board ID, sampling frequency, ordered channel names and relative board timestamps. Compare that metadata to the model's exact configuration before inference. A channel or frequency mismatch is an error, never silent reordering or resampling.

BrainFlow playback uses PlaybackSource(file, master_board), with files in BrainFlow's own recording format. Raw EDF is handled by RecordedSource after reading through MNE. Stop and close in a finally block. Before publishing live-hardware accuracy, validate board timestamps, units, filter state, dropped-data behavior, full channel mapping and task protocol experimentally.
