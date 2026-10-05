# hyperproc.correct.pipeline.footprint_overlap

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def footprint_overlap(ds_a: xr.Dataset, ds_b: xr.Dataset)
```

Intersection of the two footprint polygons: ``(area, bounds)`` with
``bounds = (x0, y0, x1, y1)``, or ``(0.0, None)`` when they do not touch.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.footprint_overlap --runtime`.
