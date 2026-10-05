# hyperproc.atmos.process

Release baseline **0.1.2**; source `hyperproc/atmos/process.py`. Choose a callable below rather than loading every declaration.

One call from an L1B granule to an atmospherically corrected GeoTIFF.

:func:`process` chains the stages the package offers and names the product by
what was done to it::

    process("EMIT_L1B_RAD_....nc", "products/")            -> <stem>_ac.tif
    process(..., stages=("ac", "brdf"))                     -> <stem>_ac_brdf.tif

The atmospheric correction runs on the sensor grid (that is where the
per-pixel geometry lives) and the result is put on a map grid afterwards:
EMIT through the granule's own geographic look-up table (GLT), exactly as
JPL's L2A ortho products are made; sensors whose L1B is already projected
(AVIRIS-3/5) need nothing; lat/lon swaths go through
:func:`hyperproc.georeference`.

## Imported aliases

- `correct` → `hyperproc.atmos.correct.correct`
- `is_complete` → `hyperproc.atmos.correct.is_complete`
- `Inputs` → `hyperproc.atmos.inputs.Inputs`

## Declared callables and classes

- [_open_for_ac](symbols/hyperproc.atmos.process._open_for_ac.md) — internal
- [_ortho_emit](symbols/hyperproc.atmos.process._ortho_emit.md) — internal
- [to_map_grid](symbols/hyperproc.atmos.process.to_map_grid.md)
- [process](symbols/hyperproc.atmos.process.process.md)

## Constant expressions

- [STAGES](constants/hyperproc.atmos.process.STAGES.md)
