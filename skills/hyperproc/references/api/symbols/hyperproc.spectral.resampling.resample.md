# hyperproc.spectral.resampling.resample

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def resample(data, source_wl=None, source_fwhm=None, *, var=None, step=None, fwhm=None, wl_range=None, wavelengths=None, like=None, sensor=None, method: str | None=None, min_coverage: float=0.5, allow_sharpening: bool=False, good_only: bool=True, return_coverage: bool=False, verbose: bool=False)
```

Resample a cube, a table of spectra or a single spectrum.

Dispatches on **type**, never on shape: an ``xarray.Dataset`` goes through
the metadata-aware path, anything array-like is treated as values whose
last axis is wavelength, whatever the other axes mean.

Args:
    data: a Dataset, or an array of any shape with wavelength last.
    source_wl, source_fwhm: required for arrays, read from a Dataset.
    var: which variable to resample; the main cube by default.
    step, fwhm, wl_range, wavelengths, like, sensor: how to name the
        target; see :func:`target_grid`.
    method: see :data:`METHODS`. None, the default, lets a ``sensor=``
        target use its own measured response and falls back to
        ``"gaussian"`` otherwise. An explicit choice always wins, which
        is how you compare a measured response against a Gaussian.
    min_coverage: target bands covered less than this become NaN.
    allow_sharpening: permit a target narrower than the source.
    good_only: drop bands flagged unusable by ``good_wavelength``.
    return_coverage: also return the per-target-band coverage.
    verbose: print what the target is and how well it is covered.

Returns:
    The same kind that went in, with the new band set. For a Dataset the
    ``wavelength`` and ``fwhm`` coordinates are replaced, ``good_wavelength``
    becomes the coverage test, and ``attrs["spectral_resampling"]`` records
    what was done. Lazy input stays lazy.

[Module and aliases](../hyperproc-spectral-resampling.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.resampling.resample --runtime`.
