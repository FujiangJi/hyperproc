#!/usr/bin/env python
"""hyperproc end to end on one EMIT granule.

    python emit_pipeline.py                  # the whole thing
    python emit_pipeline.py --stage read     # stop after reading and exporting
    python emit_pipeline.py --source copy    # skip the archive, use tests/data

EMIT is the only sensor here whose window indexes a **detector** grid. The
retrieval runs on the raw 1280 x 1242 detector array, while the L2A is
orthorectified onto a map grid, so the same rows and columns mean two
different places - on the granule this searches for, the tutorial's
600 720 600 720 lands out at sea. `subset="detector"` reopens the L1B with
`ortho=False`, windows that, and selects both levels by the ground it covers.

The default window is over vegetation on that granule: NDVI +0.72, 97 %
vegetated. Step 2 reports what your window actually contains, so a window of
open water shows up before the expensive part rather than after it.

Downloading matches the L1B and L2A by name, because the comparison at the end
only means anything if the two are the same overpass.
"""
from pipeline import SensorConfig, run

CONFIG = SensorConfig(
    name="EMIT",
    l1_glob="EMIT/EMIT_L1B_RAD_*.nc",
    l2_glob="EMIT/EMIT_L2A_RFL_*.nc",
    window={"y": (1080, 1200), "x": (840, 960)},   # vegetation, not the water
    subset="detector",                             # detector grid -> ground
    source="cmr",
    search=("EMIT", "L1B", "L2A"),
    scene="EMIT_L1B_RAD_002_20230401T203751*",     # the granule the window is on
    pair=("L1B_RAD", "L2A_RFL"),                   # same overpass, both levels
    bbox=(-121.0, 34.0, -119.8, 35.1),
    date=("2023-01-01", "2024-12-31"),
    max_cloud=20.0,
    note="the window indexes the detector grid, not the map grid",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
