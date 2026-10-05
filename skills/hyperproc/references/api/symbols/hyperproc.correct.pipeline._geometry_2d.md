# hyperproc.correct.pipeline._geometry_2d

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _geometry_2d(ds: xr.Dataset, keys=GEOMETRY, need=GEOMETRY) -> dict
```

Geometry layers as float64 radians (NaN where missing). Layers in
``need`` must exist; the others are filled with NaN when absent, so a
scene with angles but no terrain layers can still take a BRDF
normalisation (not a topographic correction).

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline._geometry_2d --runtime`.
