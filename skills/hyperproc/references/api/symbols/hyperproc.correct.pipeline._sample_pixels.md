# hyperproc.correct.pipeline._sample_pixels

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _sample_pixels(ds: xr.Dataset, fraction: float, max_pixels, seed: int, edge_px: int, topo_calc: dict, brdf_calc: dict) -> Sample
```

Whole-image masks, random pixel draw, all-pixel topographic sums (two passes).

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline._sample_pixels --runtime`.
