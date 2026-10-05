# hyperproc.spectral.bands.band_at

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def band_at(ds: xr.Dataset, wavelength: float, var: str | None=None, tolerance: float=TOLERANCE, good_only: bool=True) -> xr.DataArray
```

The band nearest ``wavelength`` nm.

Args:
    ds: dataset with a wavelength cube.
    wavelength: what to look for, nm.
    var: variable name; the main cube by default.
    tolerance: how far the nearest band may sit from the request.
    good_only: ignore bands flagged unusable by ``good_wavelength``.
        Falls back to all bands, with a warning, if that leaves nothing.

Returns:
    The 2-D slice, with ``wavelength_requested`` and the band's own
    wavelength in its attrs.

Raises:
    ValueError: nothing lies within ``tolerance``. The message says what
        was asked for and what the nearest band actually is, because on a
        VNIR-only sensor that is the whole story.

[Module and aliases](../hyperproc-spectral-bands.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.bands.band_at --runtime`.
