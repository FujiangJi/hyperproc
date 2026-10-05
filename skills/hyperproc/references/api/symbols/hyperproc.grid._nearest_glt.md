# hyperproc.grid._nearest_glt

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _nearest_glt(lat, lon, gx, gy, ok, epsg, radius, resolution, fill_holes)
```

Nearest source pixel per output cell, rejected beyond ``radius``.

This is what pyresample's ``radius_of_influence`` does. Dilating a
forward-mapped GLT instead - the obvious cheap approach - fails twice on a
wide swath: it smears the edge pixel outward past the real swath boundary,
and it still cannot reach across the gaps where pixels are widest.

[Module and aliases](../hyperproc-grid.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.grid._nearest_glt --runtime`.
