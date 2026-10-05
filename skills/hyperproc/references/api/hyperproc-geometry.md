# hyperproc.geometry

Release baseline **0.1.2**; source `hyperproc/geometry.py`. Choose a callable below rather than loading every declaration.

Per-pixel geometry checks shared by the airborne readers.

Topographic and BRDF correction both lean on ``slope``, ``aspect`` and
``cos_i``, and at least one product family (AVIRIS-3) ships them in a
convention nothing downstream expects. Rather than hard-code which instrument
is affected, these helpers *measure* it against the granule's own DEM. They
live here, not in a sensor module, so that AVIRIS and NEON - and whatever comes
next - test the same way and neither imports the other.

## Declared callables and classes

- [check_geometry](symbols/hyperproc.geometry.check_geometry.md)
- [fix_slope_convention](symbols/hyperproc.geometry.fix_slope_convention.md)
