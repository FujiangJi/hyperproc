# hyperproc.io._write_cube

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _write_cube(ds: xr.Dataset, path, var, driver: str, compress, overviews, overview_resampling: str, interleave: str | None) -> Path
```

Shared writer for every format: CRS, streaming, band labels, metadata.

The streaming rules here were expensive to find and are format independent,
so both writers use them rather than keeping two copies that drift.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io._write_cube --runtime`.
