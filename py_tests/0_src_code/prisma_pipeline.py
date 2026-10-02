#!/usr/bin/env python
"""hyperproc end to end on one PRISMA scene.

    python prisma_pipeline.py
    python prisma_pipeline.py --stage read

PRISMA is the one sensor here whose two levels are on **different grids**: the
L1 is a raw swath and the L2D is geocoded onto UTM. Applying the same window
numbers to both would compare two different pieces of ground, so the pipeline
converts the L1 window's coordinates into the L2D's CRS and selects that
extent - `subset="reproject"` below.

The L1 is opened with `latlon=True`, without which a swath has no coordinates
to convert.

ASI runs no public search API, so the scene is whatever is in tests/data;
scenes are ordered through https://prisma.asi.it/ .
"""
from pipeline import SensorConfig, run

CONFIG = SensorConfig(
    name="PRISMA",
    l1_glob="PRISMA/PRS_L1_STD_OFFL_*.he5",
    l2_glob="PRISMA/PRS_L2D_STD_*.he5",
    window={"y": (400, 600), "x": (400, 600)},
    l1_open={"latlon": True},   # a swath needs coordinates before it can be matched
    subset="reproject",         # L1 swath -> L2D UTM
    source="copy",
    note="L1 is a swath, L2D is UTM; the window is carried across by coordinate",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
