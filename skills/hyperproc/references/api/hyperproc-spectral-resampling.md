# hyperproc.spectral.resampling

Release baseline **0.1.2**; source `hyperproc/spectral/resampling.py`. Choose a callable below rather than loading every declaration.

Spectral resampling: put a cube, or a spectrum, on another band set.

Resampling is a fixed linear map. Once the weights are known, moving a whole
cube is one matrix multiply, which is why nothing here loops over pixels::

    import hyperproc as hp
    hp.resample(ds, step=10)                       # a 10 nm grid
    hp.resample(ds, step=10, fwhm=15)              # 10 nm spacing, 15 nm bands
    hp.resample(ds, like=other)                    # match another sensor's bands
    hp.resample(ds, sensor="SENTINEL2A")           # a real instrument
    hp.resample(spectra, source_wl=wl, step=10)    # an array of spectra, same maths

Two numbers, not one
--------------------
"Spectral resolution" is two independent things and every sensor in this
package has them different: the **spacing** between band centres and the
**FWHM** of each band. EMIT samples every 7.44 nm with 8.4 nm bands, PRISMA
every 9.25 nm with bands from 8.9 to 15.3 nm. So ``step`` and ``fwhm`` are
separate arguments, and leaving ``fwhm`` out makes it equal to ``step``, the
contiguous convention.

Two guards
----------
**Coverage.** A target band whose response falls partly outside the source's
range, or into a water-vapour gap, is reported with the fraction of its
response that the source actually measured, and becomes NaN below
``min_coverage``. Renormalising over whatever bands happened to be there is
the default behaviour of most implementations and it silently turns a 43 %
sample into a confident-looking number.

**Sharpening.** Resampling cannot raise spectral resolution. Asking EMIT, with
8.4 nm bands, for a 2 nm grid interpolates and calls it measurement, so it is
refused unless ``allow_sharpening=True``.

Methods
-------
``"gaussian"``
    Both source and target bands are Gaussians of their own FWHM, and the
    weight is their overlap integral, which has a closed form. The default.
``"box"``
    Source band as a rectangle of its FWHM, target as a Gaussian, weights from
    the overlap. This is what Spectral Python's ``BandResampler`` does, kept so
    earlier results stay reproducible.
``"response"``
    Uses a measured response function per target band. See
    :mod:`hyperproc.spectral.srf` for the instruments that ship one.
``"linear"``, ``"cubic"``, ``"nearest"``
    Interpolation at the target centres, ignoring band width. Right when the
    FWHM is unknown, or when the target bands are no wider than the source.

## Declared exports

`METHODS`, `build_fwhm`, `resampling_matrix`, `resample`, `target_grid`

## Imported aliases

- `main_var` → `hyperproc.io.main_var`
- `good_bands` → `hyperproc.spectral.bands.good_bands`

## Declared callables and classes

- [_sigma](symbols/hyperproc.spectral.resampling._sigma.md) — internal
- [_normal_cdf](symbols/hyperproc.spectral.resampling._normal_cdf.md) — internal
- [build_fwhm](symbols/hyperproc.spectral.resampling.build_fwhm.md)
- [_merged_intervals](symbols/hyperproc.spectral.resampling._merged_intervals.md) — internal
- [coverage_of](symbols/hyperproc.spectral.resampling.coverage_of.md)
- [_weights_gaussian](symbols/hyperproc.spectral.resampling._weights_gaussian.md) — internal
- [_weights_box](symbols/hyperproc.spectral.resampling._weights_box.md) — internal
- [_weights_interp](symbols/hyperproc.spectral.resampling._weights_interp.md) — internal
- [_weights_response](symbols/hyperproc.spectral.resampling._weights_response.md) — internal
- [resampling_matrix](symbols/hyperproc.spectral.resampling.resampling_matrix.md)
- [target_grid](symbols/hyperproc.spectral.resampling.target_grid.md)
- [_apply_block](symbols/hyperproc.spectral.resampling._apply_block.md) — internal
- [resample](symbols/hyperproc.spectral.resampling.resample.md)
- [_resample_dataset](symbols/hyperproc.spectral.resampling._resample_dataset.md) — internal

## Constant expressions

- [METHODS](constants/hyperproc.spectral.resampling.METHODS.md)
- [SQRT_8LN2](constants/hyperproc.spectral.resampling.SQRT_8LN2.md)
