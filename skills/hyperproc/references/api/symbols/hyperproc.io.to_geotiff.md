# hyperproc.io.to_geotiff

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def to_geotiff(ds: xr.Dataset, path: str | Path, var: str | None=None, compress: str='deflate', overviews: bool | list[int] | None=None, overview_resampling: str='average') -> Path
```

Write a cube to a multi-band GeoTIFF, one band per wavelength.

Band descriptions are set to the wavelength in nm, so QGIS and ArcGIS show
``650.4 nm`` rather than ``Band 12``. With ``overviews`` the file also gets
internal pyramids (what QGIS's *Build Overviews* does), so a GIS can draw the
whole cube without reading it at full resolution.

For a header that states the wavelengths as numbers rather than as band
labels, and that can carry a bad-band list, see :func:`to_envi`.

Args:
    ds: dataset from :func:`hyperproc.open`. Must be orthorectified -
        a sensor-grid cube has no CRS to write.
    path: output ``.tif``, or a **directory**, in which case the file is
        named after the source granule - ``EMIT_L2A_RFL_..._002.nc``
        becomes ``EMIT_L2A_RFL_..._002.tif``. Parents are created.
    var: which variable to write. Defaults to the cube variable.
    compress: GeoTIFF compression. ``"deflate"`` is lossless and roughly
        halves the file; pass ``None`` for none.
    overviews: ``True`` builds internal overview pyramids with factors
        2, 4, 8, ... until the coarsest level is under 256 px; a list gives
        the factors explicitly (``[2, 4, 8, 16]``); ``None`` (default)
        builds none. See :func:`build_overviews`.
    overview_resampling: how overview pixels are computed - ``"average"``
        (default, right for reflectance), ``"nearest"``, ``"bilinear"``,
        ``"cubic"``, ``"mode"`` ...

Returns:
    The path written.

Raises:
    ValueError: the dataset is on the sensor grid and has no CRS.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.to_geotiff --runtime`.
