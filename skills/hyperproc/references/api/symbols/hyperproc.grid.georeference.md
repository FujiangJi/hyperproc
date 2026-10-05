# hyperproc.grid.georeference

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def georeference(ds: xr.Dataset, epsg: int | None=None, resolution: float | None=None, radius: float | None=None, fill_holes: bool=True, like: xr.Dataset | None=None) -> xr.Dataset
```

Resample a lat/lon swath onto a regular projected grid.

Args:
    ds: dataset carrying 2-D ``lat`` and ``lon`` variables.
    epsg: target CRS. Defaults to the UTM zone under the scene centre,
        which for PRISMA reproduces the zone ASI uses for its own L2D.
        Pass ``4326`` for plate carree.
    resolution: output pixel size in target-CRS units. ``None`` uses the
        sensor's documented default where one exists - PACE gets 0.01 deg
        (~1.1 km), matching its nadir pixel - and otherwise measures the
        median spacing between adjacent swath pixels, which for PRISMA
        lands on ~30 m. Pass ``"native"`` to always measure, or a number
        to set it yourself.
    radius: hard upper bound of the search, in metres. Defaults to twice
        the 99th-percentile source pixel half-diagonal.
    fill_holes: a cell is filled when its nearest source pixel lies within
        that pixel's own half-diagonal (its footprint), so gaps where the
        grid is finer than the swath close, while nothing is invented past
        the swath edge or the along-track ends. ``False`` accepts only
        source pixels inside the cell itself.
    like: a projected dataset whose grid to reproduce exactly (CRS,
        pixel size, origin and shape), for example ASI's PRISMA L2D, so
        the result compares cell for cell. Overrides ``epsg`` and
        ``resolution``; north-up grids only.

Returns:
    A new Dataset on ``(y, x)`` with ``crs``/``transform`` set, ready for
    :func:`hyperproc.to_geotiff`. ``lat``/``lon`` are dropped; a ``valid``
    mask marks cells the swath actually covers.

Raises:
    ValueError: ``ds`` has no ``lat``/``lon``, or is already projected.

[Module and aliases](../hyperproc-grid.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.grid.georeference --runtime`.
