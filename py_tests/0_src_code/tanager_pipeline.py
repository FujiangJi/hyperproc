#!/usr/bin/env python
"""hyperproc end to end on one Tanager scene.

    python tanager_pipeline.py
    python tanager_pipeline.py --stage read

Planet ships Tanager as two orthorectified HDF5 files on one grid - radiance
and surface reflectance - so the window is the same rows and columns on both.
At 426 bands it is the finest spectral sampling of the five.

Planet distributes Tanager commercially, so there is no search to run; the
scene is whatever is in tests/data. A free sample catalogue of core imagery is
published as an open STAC at
https://www.planet.com/data/stac/tanager-core-imagery/catalog.json , which is
browsed rather than queried.
"""
from pipeline import SensorConfig, run

CONFIG = SensorConfig(
    name="Tanager",
    l1_glob="Tanager/*_ortho_radiance_hdf5.h5",
    l2_glob="Tanager/*_ortho_sr_hdf5.h5",
    window={"y": (230, 430), "x": (290, 490)},
    subset="isel",
    source="copy",
    note="Planet distributes Tanager commercially; no public search API",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
