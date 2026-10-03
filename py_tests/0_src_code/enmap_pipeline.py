#!/usr/bin/env python
"""hyperproc end to end on one EnMAP scene.

    python enmap_pipeline.py                 # the whole thing
    python enmap_pipeline.py --stage read    # stop after reading and exporting
    python enmap_pipeline.py --source copy   # skip the archive, use tests/data
    python enmap_pipeline.py --accept-dlr-policy   # first download, new account

EnMAP is the easiest of the five to compare: DLR delivers L1C radiance and
L2A reflectance **on the same UTM grid**, so the window is the same rows and
columns on both and no reprojection is needed to line them up.

The atmospheric route starts from L1C rather than L1B. L1B ships the VNIR and
SWIR detectors as two unregistered files - they are brought into register in
the L1C geometric processing - so L1B is the wrong input for a retrieval that
assumes one cube on one grid.

Downloading needs a DLR account cleared for EnMAP
(https://www.enmap.org/data_access/). Without ENMAP_USERNAME/ENMAP_PASSWORD
or ~/.netrc it asks at the terminal, and stops if you give none. The scene is
the tile in tests/data; DLR's archive copy carries a later processing date
and serves the images as *_COG.TIF, which hyperproc reads the same way.
"""
import re

from pipeline import SensorConfig, run


def mate(l1_name):
    """The L2A of the same tile, by datatake, start time and tile number.

    The two levels are processed separately, so their names end in different
    processing timestamps and no substring swap turns one into the other.
    """
    return "*" + re.search(r"DT\d+_\d{8}T\d{6}Z_\d{3}", l1_name).group(0) + "*"


CONFIG = SensorConfig(
    name="EnMAP",
    l1_glob="EnMAP/ENMAP01-____L1C-*-SPECTRAL_IMAGE*.TIF",   # plain or _COG
    l2_glob="EnMAP/ENMAP01-____L2A-*-SPECTRAL_IMAGE*.TIF",
    window={"y": (500, 700), "x": (600, 800)},     # 200 x 200, as the tutorial
    subset="isel",                                 # both levels share a UTM grid
    source="dlr",
    search=("ENMAP", "L1C", "L2A"),
    scene="*DT0000191711_20260507T195102Z_003_*",  # Klamath / Mt Shasta, 0 % cloud
    pair=mate,
    bbox=(-122.95, 41.55, -122.75, 41.70),         # inside that tile
    date="2026-05-07",
    note="L1C, not L1B: the two L1B detectors are not co-registered",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
