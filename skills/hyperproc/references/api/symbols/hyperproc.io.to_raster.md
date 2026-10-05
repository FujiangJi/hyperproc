# hyperproc.io.to_raster

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def to_raster(ds: xr.Dataset, path: str | Path, format: str='GTiff', **kwargs) -> Path
```

Write a cube in either format. ``format`` is ``"GTiff"`` or ``"ENVI"``.

A single door for code that takes the format as a setting; the keyword
arguments are those of :func:`to_geotiff` or :func:`to_envi`.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.to_raster --runtime`.
