# hyperproc.correct.mcd43.grid_for

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def grid_for(bounds, res: float=RES_DEG, pad: float=0.05) -> tuple
```

Snap ``(w, s, e, n)`` outward onto a global ``res``-degree grid.

Returns ``(transform, nx, ny)``. Snapping means two scenes that overlap ask
for the same cells, so the cache is shared and there is no half-pixel shift
between them.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.grid_for --runtime`.
