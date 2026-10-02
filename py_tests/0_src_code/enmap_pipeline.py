#!/usr/bin/env python
"""hyperproc end to end on one EnMAP scene.

    python enmap_pipeline.py                 # the whole thing
    python enmap_pipeline.py --stage read    # stop after reading and exporting
    python enmap_pipeline.py --source copy   # skip the archive, use tests/data

EnMAP is the easiest of the five to compare: DLR delivers L1C radiance and
L2A reflectance **on the same UTM grid**, so the window is the same rows and
columns on both and no reprojection is needed to line them up.

The atmospheric route starts from L1C rather than L1B. L1B ships the VNIR and
SWIR detectors as two unregistered files - they are brought into register in
the L1C geometric processing - so L1B is the wrong input for a retrieval that
assumes one cube on one grid.

Downloading needs a DLR EnMAP Access Service account; without one this falls
back to the copy in tests/data and says so.
"""
from pipeline import SensorConfig, run

CONFIG = SensorConfig(
    name="EnMAP",
    l1_glob="EnMAP/ENMAP01-____L1C-*-SPECTRAL_IMAGE.TIF",
    l2_glob="EnMAP/ENMAP01-____L2A-*-SPECTRAL_IMAGE.TIF",
    window={"y": (500, 700), "x": (600, 800)},     # 200 x 200, as the tutorial
    subset="isel",                                 # both levels share a UTM grid
    source="dlr",
    search=("ENMAP", "L1C", "L2A"),
    note="L1C, not L1B: the two L1B detectors are not co-registered",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
