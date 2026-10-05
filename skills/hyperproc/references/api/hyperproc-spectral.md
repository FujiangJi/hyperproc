# hyperproc.spectral

Release baseline **0.1.2**; source `hyperproc/spectral/__init__.py`. Choose a callable below rather than loading every declaration.

Per-spectrum transforms: a cube goes in, a cube comes out.

    hyperproc.spectral.bands        addressing a band by wavelength
    hyperproc.spectral.smoothing    Savitzky-Golay and moving-average smoothing
    hyperproc.spectral.continuum    continuum removal by convex hull
    hyperproc.spectral.derivatives  first and second derivatives
    hyperproc.spectral.resampling   putting a cube on another band set
    hyperproc.spectral.srf          published response functions, fetched and cached

Operations that reduce a spectrum to one number per pixel - spectral indices
and absorption depths - live in :mod:`hyperproc.features` instead, because
what comes out of them is a map, not a cube.

## Declared exports

`bands`, `continuum`, `derivatives`, `resampling`, `smoothing`, `srf`, `TOLERANCE`, `band_at`, `good_bands`, `runs_of_good_bands`, `continuum_removal`, `derivative`, `smooth_spectra`, `find_spikes`, `spline_gapfill`, `PRISMA_ARTEFACT_RANGES`, `PRISMA_MASK_AFTER`, `METHODS`, `build_fwhm`, `resample`, `resampling_matrix`, `target_grid`

## Imported aliases

- `bands` → `hyperproc.spectral.bands`
- `continuum` → `hyperproc.spectral.continuum`
- `derivatives` → `hyperproc.spectral.derivatives`
- `resampling` → `hyperproc.spectral.resampling`
- `smoothing` → `hyperproc.spectral.smoothing`
- `srf` → `hyperproc.spectral.srf`
- `TOLERANCE` → `hyperproc.spectral.bands.TOLERANCE`
- `band_at` → `hyperproc.spectral.bands.band_at`
- `good_bands` → `hyperproc.spectral.bands.good_bands`
- `runs_of_good_bands` → `hyperproc.spectral.bands.runs_of_good_bands`
- `continuum_removal` → `hyperproc.spectral.continuum.continuum_removal`
- `derivative` → `hyperproc.spectral.derivatives.derivative`
- `METHODS` → `hyperproc.spectral.resampling.METHODS`
- `build_fwhm` → `hyperproc.spectral.resampling.build_fwhm`
- `resample` → `hyperproc.spectral.resampling.resample`
- `resampling_matrix` → `hyperproc.spectral.resampling.resampling_matrix`
- `target_grid` → `hyperproc.spectral.resampling.target_grid`
- `PRISMA_ARTEFACT_RANGES` → `hyperproc.spectral.smoothing.PRISMA_ARTEFACT_RANGES`
- `PRISMA_MASK_AFTER` → `hyperproc.spectral.smoothing.PRISMA_MASK_AFTER`
- `find_spikes` → `hyperproc.spectral.smoothing.find_spikes`
- `smooth_spectra` → `hyperproc.spectral.smoothing.smooth_spectra`
- `spline_gapfill` → `hyperproc.spectral.smoothing.spline_gapfill`

## Declared callables and classes

