# hyperproc.readers.desis.open_desis

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_desis(path: str | Path, wl_range: tuple[float, float] | None=None, quality: bool=True, band_quality: bool=False, apply_scale: bool=True) -> xr.Dataset
```

Open a DESIS granule.

Args:
    path: the ``*-SPECTRAL_IMAGE.tif``. The ``METADATA.xml`` and quality
        siblings are found beside it by name.
    wl_range: ``(min_nm, max_nm)`` band subset. DESIS covers 401-1000 nm.
    quality: attach the L2A ``QL_QUALITY-2`` layers - ``shadow``, ``land``,
        ``snow``, ``haze_land``, ``haze_water``, ``cloud_land``,
        ``cloud_water``, ``water``, plus ``aot550`` and ``wv_cm``. A
        combined ``cloud`` is derived from the two cloud flags.
    band_quality: attach the 235-band per-band quality raster as
        ``band_quality``. Adds a uint8 array the size of the cube.
    apply_scale: convert DN to physical units with the per-band gain and
        offset. ``False`` returns raw ``int16`` DN, for debugging.

Returns:
    Dataset with ``radiance`` or ``reflectance`` on ``(y, x, wavelength)``
    and ``wavelength``/``fwhm`` coordinates in nm.

[Module and aliases](../hyperproc-readers-desis.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.desis.open_desis --runtime`.
