# hyperproc.io.to_geotiff_2d

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def to_geotiff_2d(ds: xr.Dataset, path: str | Path, var: str, overviews: bool | list[int] | None=None, overview_resampling: str='average', tags: dict | None=None, format: str='GTiff') -> Path
```

Write a single 2-D layer (``sza``, ``elev``, ``cloud``, ...) to GeoTIFF.

``path`` may be a directory, in which case the file is named
``<granule>_<var>.tif``. ``tags`` are written as GeoTIFF metadata, which is
how a flag layer carries its own bit meanings.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.to_geotiff_2d --runtime`.
