# hyperproc.spectral.smoothing.smooth_spectra

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def smooth_spectra(ds: xr.Dataset, var: str | None=None, window: int=5, order: int=2, method: str='savgol', good_only: bool=True) -> xr.Dataset
```

A copy of ``ds`` whose spectra are smoothed along wavelength.

Args:
    ds: dataset with a ``(y, x, wavelength)`` cube.
    var: which variable to smooth; the cube variable by default.
    window: filter length in bands, odd, at least ``order + 2``.
    order: polynomial order for ``"savgol"``.
    method: ``"savgol"`` (Savitzky-Golay, keeps peak shape) or
        ``"moving"`` (running mean).
    good_only: smooth only runs of bands flagged usable by
        ``good_wavelength``, so the filter never reaches across the
        water-vapour gaps. With False every band is one run.

Returns:
    A new dataset; the smoothed variable carries ``smoothing`` in its
    attrs and the dataset carries ``spectral_smoothing``. Uncertainty
    layers are dropped, because smoothing makes them wrong.

[Module and aliases](../hyperproc-spectral-smoothing.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.smoothing.smooth_spectra --runtime`.
