# hyperproc.spectral.smoothing.spline_gapfill

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def spline_gapfill(ds: xr.Dataset, var: str | None=None, df: float=60.0, threshold: float=0.018, despike: bool=True, exclude=PRISMA_ARTEFACT_RANGES, mask_after=PRISMA_MASK_AFTER, min_points: int=20, keep_fill_flag: bool=True) -> xr.Dataset
```

Despike, mask, spline-smooth with gap filling, then mask again.

The published PRISMA route, in four steps per spectrum:

1. mark upward spikes with :func:`find_spikes` and blank them,
2. blank ``exclude``, the regions where the instrument's spectral shift
   leaves artefacts around the gaseous absorptions,
3. fit a smoothing spline with ``df`` degrees of freedom through what
   survives and evaluate it at **every** wavelength, which smooths and
   fills the blanked bands in one step,
4. blank ``mask_after``, the deep water absorptions and the SWIR tail.

This is not what :func:`smooth_spectra` does, and the difference is the
point. That one filters inside runs of usable bands and never crosses a
gap, so it cannot invent a value. This one crosses them deliberately. On a
230-band PRISMA scene about 120 bands come out with values, and some of
those are spline fill rather than measurement, which is what
``keep_fill_flag`` records.

The spline is R's ``smooth.spline``, ported in
:mod:`hyperproc.spectral._smoothspline` and verified against it.

Args:
    ds: dataset with a ``(y, x, wavelength)`` cube.
    var: variable to smooth; the main cube by default.
    df: degrees of freedom for the spline.
    threshold: spike height for step 1, in reflectance units.
    despike: run step 1 at all.
    exclude: ranges blanked before fitting (nm).
    mask_after: ranges blanked after fitting (nm).
    min_points: a spectrum with fewer surviving bands is left as NaN.
    keep_fill_flag: attach ``spline_filled``, True where a reported value
        came from the spline rather than from the instrument.

Returns:
    A copy of ``ds`` with the cube replaced, recording what was done in
    ``attrs["spline_gapfill"]``. Uncertainty is dropped: the spline
    correlates bands and invents some of them.

[Module and aliases](../hyperproc-spectral-smoothing.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.smoothing.spline_gapfill --runtime`.
