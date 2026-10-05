# hyperproc.readers.neon.open_neon

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_neon(path: str | Path, wl_range: tuple[float, float] | None=None, good_bands_only: bool=False, geometry: bool=True, extras: bool=True, classes: bool=True, fix_geometry: bool | str='auto', chunks: str | tuple | None='auto') -> xr.Dataset
```

Open a NEON DP1.30006.001 flightline.

Args:
    path: ``NEON_D??_SITE_DP1_YYYYMMDD_HHMMSS_reflectance.h5``.
    wl_range: ``(min_nm, max_nm)``, applied before any data is read.
    good_bands_only: NaN the bands inside NEON's own water-vapour windows
        (``Band_Window_1/2_Nanometers``), keeping the band count.
    geometry: attach ``slope``, ``aspect``, ``elev``, ``cos_i``,
        ``path_length``, per-pixel ``vza``/``vaa``, the line's scalar
        ``sza``/``saa`` broadcast to the grid, and a derived ``raa``.
    extras: attach ``aot``, ``wv``, ``sky_view``, ``visibility``.
    classes: attach ``hcw_class`` and ``ddv_class`` with their lookup
        tables, plus ``cast_shadow_raw``.
    fix_geometry: ``"auto"`` runs :func:`hyperproc.check_geometry` against
        the shipped DEM and corrects slope/``cos_i`` only if the product
        stores slope from vertical (NEON does not, on the lines here -
        the verdict lands in ``attrs["geometry_check"]``). ``True``
        forces it, ``False`` leaves every layer as delivered.
    chunks: dask chunking. ``"auto"`` aligns to the file's gzip chunks
        with all bands together; ``None`` reads eagerly.

Returns:
    ``xarray.Dataset`` with ``reflectance(y, x, wavelength)`` in 0-1,
    ``wavelength``/``fwhm``/``good_wavelength`` coordinates, and
    ``attrs["transform"]`` in GDAL order on a north-up UTM grid.

[Module and aliases](../hyperproc-readers-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.neon.open_neon --runtime`.
