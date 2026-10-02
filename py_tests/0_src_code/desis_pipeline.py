#!/usr/bin/env python
"""hyperproc end to end on one DESIS scene.

    python desis_pipeline.py
    python desis_pipeline.py --stage read

DESIS has to be copied rather than downloaded, and that is a property of the
archive rather than of this script: **DLR publishes only DESIS L2A openly**.
L1B and L1C are ordered commercially through Teledyne Brown, so the L1C this
pipeline corrects cannot be fetched by hyperproc.search at all - run
`hyperproc.archive.describe()` and it says so.

Like EnMAP, both levels sit on one UTM grid, so the window is the same rows
and columns on each.
"""
from pipeline import SensorConfig, run

CONFIG = SensorConfig(
    name="DESIS",
    l1_glob="DESIS/DESIS-HSI-L1C-*-SPECTRAL_IMAGE.tif",
    l2_glob="DESIS/DESIS-HSI-L2A-*-SPECTRAL_IMAGE.tif",
    window={"y": (600, 800), "x": (600, 800)},
    subset="isel",
    source="copy",            # only L2A is public; the L1C must come from disk
    note="DLR publishes only DESIS L2A; the L1C is not downloadable",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
