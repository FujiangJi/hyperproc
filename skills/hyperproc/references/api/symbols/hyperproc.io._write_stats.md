# hyperproc.io._write_stats

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _write_stats(path: Path) -> None
```

Embed per-band min/max/mean/std.

Without these GDAL reports no statistics and QGIS falls back to a default
stretch, which for values like latitude 37.1 or longitude -80.9 renders as
a blank or solid-black layer.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io._write_stats --runtime`.
