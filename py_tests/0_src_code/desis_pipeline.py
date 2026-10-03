#!/usr/bin/env python
"""hyperproc end to end on one DESIS scene.

    python desis_pipeline.py                     # the scene, copied from tests/data
    python desis_pipeline.py --stage read
    python desis_pipeline.py --source download   # ask DLR anyway; it has no copy

DESIS cannot be downloaded here, and that is a property of the archive rather
than of this script: **DLR publishes only DESIS L2A openly, and only for
2018-2021**. L1B and L1C are ordered commercially through Teledyne Brown, so
the L1C this pipeline corrects cannot be fetched by hyperproc.search at all -
run `hyperproc.archive.describe()` and it says so.

The scene is DT0117241957_024, 2024-01-17, on the NE Venezuelan coast: the one
in tests/data, which holds both its L1C and its L2A. DLR publishes no L2A for
it, so it is copied rather than downloaded. Run from a copy of these scripts
outside the repository, set HYPERPROC_TESTS_DATA to the repository's
tests/data so the copy can find it.

Like EnMAP, both levels sit on one UTM grid, so the window is the same rows
and columns on each.
"""
from pipeline import SensorConfig, run

CONFIG = SensorConfig(
    name="DESIS",
    l1_glob="DESIS/DESIS-HSI-L1C-*-SPECTRAL_IMAGE.tif",
    l2_glob="DESIS/DESIS-HSI-L2A-*-SPECTRAL_IMAGE.tif",
    window={"y": (600, 800), "x": (600, 800)},     # NDVI +0.80, 92 % vegetated
    subset="isel",
    source="copy",                                 # DLR has no L2A for this scene
    search=("DESIS", "L1C", "L2A"),
    scene="*DT0117241957_024-*",                   # NE Venezuela coast, 2024-01-17
    bbox=(-63.90, 10.40, -63.70, 10.60),           # inside that scene
    date="2024-01-17",
    note="the 2024 scene from tests/data; DLR publishes no DESIS L2A after 2021",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
