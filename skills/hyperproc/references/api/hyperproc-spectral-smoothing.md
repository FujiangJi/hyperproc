# hyperproc.spectral.smoothing

Release baseline **0.1.2**; source `hyperproc/spectral/smoothing.py`. Choose a callable below rather than loading every declaration.

Cosmetic spectral smoothing.

A per-pixel optimal-estimation retrieval leaves real band-to-band structure:
on the EMIT test granule its size matches JPL's own product exactly, and on
Tanager it sits well below the retrieval's posterior uncertainty. Some
providers publish spectra with that structure removed (Planet's Tanager
reflectance is smooth to four decimals in the near infrared, which no
per-pixel retrieval produces), so a product compared against theirs can look
noisy without being wrong.

:func:`smooth_spectra` makes the same cosmetic change, explicitly and
reversibly. It never runs by itself: correction and export leave the
retrieval as it is, and the result records what was done in
``attrs["spectral_smoothing"]``.

**It is cosmetic.** Smoothing correlates neighbouring bands, so it invalidates
the posterior uncertainty and biases anything that measures narrow features:
fit absorption depths, continuum removal and spectral indices on the
unsmoothed cube.

## Declared exports

`smooth_spectra`, `find_spikes`, `spline_gapfill`, `PRISMA_ARTEFACT_RANGES`, `PRISMA_MASK_AFTER`

## Imported aliases

- `main_var` → `hyperproc.io.main_var`
- `_runs` → `hyperproc.spectral.bands.runs_of_good_bands`

## Declared callables and classes

- [_smooth_block](symbols/hyperproc.spectral.smoothing._smooth_block.md) — internal
- [smooth_spectra](symbols/hyperproc.spectral.smoothing.smooth_spectra.md)
- [find_spikes](symbols/hyperproc.spectral.smoothing.find_spikes.md)
- [_in_ranges](symbols/hyperproc.spectral.smoothing._in_ranges.md) — internal
- [_one_blas_thread](symbols/hyperproc.spectral.smoothing._one_blas_thread.md) — internal
- [_gapfill_block](symbols/hyperproc.spectral.smoothing._gapfill_block.md) — internal
- [spline_gapfill](symbols/hyperproc.spectral.smoothing.spline_gapfill.md)

## Constant expressions

- [PRISMA_ARTEFACT_RANGES](constants/hyperproc.spectral.smoothing.PRISMA_ARTEFACT_RANGES.md)
- [PRISMA_MASK_AFTER](constants/hyperproc.spectral.smoothing.PRISMA_MASK_AFTER.md)
