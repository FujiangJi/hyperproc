# hyperproc.correct.pipeline._cloud_stats

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _cloud_stats(index: dict, valid=None) -> dict
```

Zhai scene statistics, or ``{"n": 0}`` (no cloud test) when the cube has
no blue/green index band - a ``wl_range`` starting above 480 nm, say.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline._cloud_stats --runtime`.
