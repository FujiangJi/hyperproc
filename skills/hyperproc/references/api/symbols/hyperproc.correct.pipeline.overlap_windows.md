# hyperproc.correct.pipeline.overlap_windows

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def overlap_windows(ds_a: xr.Dataset, ds_b: xr.Dataset, max_rows: int=1200)
```

Pixel windows ``(y0, y1, x0, x1)`` in each cube covering one common map
region inside the overlap of their footprints, with roughly ``max_rows``
rows in each (a rotated grid needs somewhat more rows to cover an
axis-aligned region). None when the footprints do not overlap.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.overlap_windows --runtime`.
