# hyperproc.grid

Release baseline **0.1.2**; source `hyperproc/grid.py`. Choose a callable below rather than loading every declaration.

Turn a swath into a map-projected grid.

Sensors that ship per-pixel latitude/longitude instead of an affine transform
(PRISMA L1/L2B/L2C, PACE, un-orthorectified EMIT) cannot be written to GeoTIFF
directly: their ground track is rotated and slightly curved, so no single
six-number transform describes it. PRISMA's L2C swath, for instance, runs about
79 degrees off north.

:func:`georeference` resamples such a dataset onto a regular north-up grid by
building a **GLT** (geometry lookup table) - the same device EMIT ships in its
own granules, and what prismaread's ``base_georef`` produces. Every output pixel
is a *verbatim copy* of one input pixel: nearest-neighbour by construction, so
no spectra are invented by interpolation.

## Declared callables and classes

- [utm_epsg](symbols/hyperproc.grid.utm_epsg.md)
- [georeference](symbols/hyperproc.grid.georeference.md)
- [latlon_grid](symbols/hyperproc.grid.latlon_grid.md)
- [_ecef](symbols/hyperproc.grid._ecef.md) — internal
- [_nearest_glt](symbols/hyperproc.grid._nearest_glt.md) — internal
- [_native_spacing](symbols/hyperproc.grid._native_spacing.md) — internal
- [_apply_glt](symbols/hyperproc.grid._apply_glt.md) — internal

## Constant expressions

- [DEFAULT_RESOLUTION_DEG](constants/hyperproc.grid.DEFAULT_RESOLUTION_DEG.md)
