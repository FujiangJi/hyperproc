# hyperproc.spectral.continuum

Release baseline **0.1.2**; source `hyperproc/spectral/continuum.py`. Choose a callable below rather than loading every declaration.

Continuum removal by the upper convex hull.

Dividing a spectrum by its own hull separates the shape of an absorption from
the brightness of the surface under it, which is what makes a feature depth
comparable between scenes and between sensors.

The hull is fitted inside each run of usable bands, never across one, so it
cannot invent a continuum over a region the instrument does not see.

## Declared exports

`continuum_removal`

## Imported aliases

- `main_var` → `hyperproc.io.main_var`
- `good_bands` → `hyperproc.spectral.bands.good_bands`
- `_runs` → `hyperproc.spectral.bands.runs_of_good_bands`

## Declared callables and classes

- [_upper_hull](symbols/hyperproc.spectral.continuum._upper_hull.md) — internal
- [_continuum_block](symbols/hyperproc.spectral.continuum._continuum_block.md) — internal
- [continuum_removal](symbols/hyperproc.spectral.continuum.continuum_removal.md)
