# hyperproc.features

Release baseline **0.1.2**; source `hyperproc/features.py`. Choose a callable below rather than loading every declaration.

Spectral features: indices and absorption depths.

What separates these from :mod:`hyperproc.spectral` is what comes out. Those
transform a cube into a cube; these reduce each spectrum to one number per
pixel, so the result is a map.

Both halves address bands by **wavelength**, never by band number, which is
what lets one call run unchanged on EMIT at 285 bands, PACE at 122 and AVIRIS
at 425::

    import hyperproc as hp
    hp.spectral_index(ds, "NDVI")                          # a named index
    hp.spectral_index(ds, "(R800 - R670) / (R800 + R670)") # or write your own
    hp.band_depth(ds, "cellulose")
    print(hp.describe_indices(ds))              # which indices this sensor can compute

Fit these on the **unsmoothed** cube: :func:`hyperproc.smooth_spectra` is
cosmetic and correlates neighbouring bands, which biases exactly the narrow
features measured here.

## Declared exports

`band_at`, `index`, `INDICES`, `band_depth`, `FEATURES`, `describe_indices`

## Imported aliases

- `main_var` → `hyperproc.io.main_var`
- `TOLERANCE` → `hyperproc.spectral.bands.TOLERANCE`
- `band_at` → `hyperproc.spectral.bands.band_at`
- `continuum_removal` → `hyperproc.spectral.continuum.continuum_removal`

## Declared callables and classes

- [_evaluate](symbols/hyperproc.features._evaluate.md) — internal
- [index](symbols/hyperproc.features.index.md)
- [describe_indices](symbols/hyperproc.features.describe_indices.md)
- [_argmin_wavelength](symbols/hyperproc.features._argmin_wavelength.md) — internal
- [band_depth](symbols/hyperproc.features.band_depth.md)

## Constant expressions

- [INDICES](constants/hyperproc.features.INDICES.md)
- [FEATURES](constants/hyperproc.features.FEATURES.md)
- [_TOKEN](constants/hyperproc.features._TOKEN.md)
- [_FUNCS](constants/hyperproc.features._FUNCS.md)
