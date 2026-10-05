# hyperproc.correct.pipeline.footprint_polygon

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def footprint_polygon(ds: xr.Dataset)
```

The cube's pixel footprint as a shapely polygon (a rotated rectangle for
flight-aligned grids). Bounding boxes overstate the overlap of rotated
swaths - two lines that never touch can still have intersecting boxes.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.footprint_polygon --runtime`.
