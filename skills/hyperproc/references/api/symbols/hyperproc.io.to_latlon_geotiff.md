# hyperproc.io.to_latlon_geotiff

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def to_latlon_geotiff(ds: xr.Dataset, path: str | Path, separate: bool=False, overviews: bool | list[int] | None=None, overview_resampling: str='average') -> Path | tuple[Path, Path]
```

Write a 2-band GeoTIFF of latitude and longitude - prismaread's ``LATLON``.

Band 1 is latitude, band 2 longitude, both WGS-84 degrees. For a projected
dataset the values are computed from the CRS and grid, so they are exact and
available whether or not the granule shipped geolocation arrays. For an
unprojected swath the granule's own ``lat``/``lon`` are written instead, and
the file carries no CRS - the same thing prismaread does.

Args:
    ds: dataset from :func:`hyperproc.open` or :func:`hyperproc.georeference`.
    path: output ``.tif``, or a directory to write ``<granule>_latlon.tif`` in.
    separate: write two single-band files, ``<granule>_lat.tif`` and
        ``<granule>_lon.tif``, instead of one two-band file. Two-band float
        rasters are awkward in QGIS, which tends to open them as an RGB
        composite with no blue channel and render them black; single-band
        files always open as greyscale.

Returns:
    The path written, or both paths when ``separate=True``.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.to_latlon_geotiff --runtime`.
