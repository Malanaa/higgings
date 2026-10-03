"""Standard-label electrode map, never individual head coordinates."""

import mne


def electrode_map(channels: list[str]) -> dict:
    montage = mne.channels.make_standard_montage("colin27_1005")
    positions = montage.get_positions()["ch_pos"]
    matched = [
        {
            "channel": name,
            "index": i,
            "x": float(positions[name][0]),
            "y": float(positions[name][1]),
        }
        for i, name in enumerate(channels)
        if name in positions
    ]
    if len(matched) < 3:
        return {
            "available": False,
            "reason": "Not enough channel labels map to the standard montage",
            "electrodes": [],
        }
    return {
        "available": True,
        "template": "MNE colin27_1005 standard label positions",
        "individualized": False,
        "electrodes": matched,
        "unmapped": [name for name in channels if name not in positions],
    }
