# hyperproc.io.build_overviews

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def build_overviews(path: str | Path, factors: list[int] | None=None, resampling: str='average', compress: str | None='deflate', min_size: int=256) -> list[int]
```

Add internal overview pyramids to an existing GeoTIFF.

This is what QGIS's *Raster > Miscellaneous > Build Overviews (Pyramids)*
and ``gdaladdo`` do: reduced-resolution copies of every band are appended
to the file so a viewer can draw it zoomed out without decoding the full
cube. The pyramids are compressed like the main image, band-interleaved,
and built on all cores. Nodata (NaN) pixels are left out of the averages.

Args:
    path: GeoTIFF to modify in place (the main image is untouched).
    factors: reduction factors, e.g. ``[2, 4, 8, 16]``. Default: powers of
        two while the coarsest level is still at least ``min_size`` px on
        its longer side.
    resampling: any :class:`rasterio.enums.Resampling` name.
    compress: compression for the overview levels; ``None`` for none.
    min_size: stops the default factor list.

Returns:
    The factors built (empty if the image is already smaller than
    ``min_size``). Size cost is roughly a third of the main image before
    compression; reading the overviews of band 1 back is
    ``rasterio.open(path).overviews(1)``.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.build_overviews --runtime`.
