#!/usr/bin/env python
"""hyperproc end to end on one PACE OCI scene.

    python pace_pipeline.py
    python pace_pipeline.py --stage ac

Two things about PACE differ from every other sensor here.

**The L1B is top-of-atmosphere reflectance, not radiance.** OCI publishes it
already divided by the solar irradiance, so `hp.main_var` on the L1B says
"reflectance" where the others say "radiance". The retrieval handles the
conversion; it is only surprising when reading the printout.

**Both levels are on the raw swath**, not a map grid, so the window indexes
the same rows and columns on each and nothing has to be reprojected - but the
products carry no CRS, which is why the geometry figure is the interesting one
and a coordinate-matched comparison is not always possible.

At 1.2 km, one PACE pixel covers more ground than a whole EnMAP window.
"""
import re

from pipeline import SensorConfig, run


def mate(l1_name):
    """The L2 of the same overpass, found by its timestamp.

    CMR prefixes a granule name with its collection, and the L1B and L2
    collections differ, so a substring swap would produce a name that
    belongs to neither. The acquisition time identifies the overpass.
    """
    return "*" + re.search(r"\d{8}T\d{6}", l1_name).group(0) + "*"

CONFIG = SensorConfig(
    name="PACE",
    l1_glob="PACE/PACE_OCI.*.L1B.V3.nc",
    l2_glob="PACE/PACE_OCI.*.L2.SFREFL.V3_1.nc",
    window={"y": (800, 1000), "x": (600, 800)},
    subset="isel",            # both levels are the same swath
    source="cmr",
    search=("PACE", "L1B", "L2"),
    pair=mate,
    note="the L1B is TOA reflectance, not radiance; both levels are a swath",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
