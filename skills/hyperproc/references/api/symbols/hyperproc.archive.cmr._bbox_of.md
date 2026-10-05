# hyperproc.archive.cmr._bbox_of

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _bbox_of(umm: dict) -> tuple[float, float, float, float] | None
```

The granule footprint as ``(west, south, east, north)``.

CMR states the footprint as a polygon, which is the honest shape for a
rotated swath, but a box is what a listing can show and what a map needs.

[Module and aliases](../hyperproc-archive-cmr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.cmr._bbox_of --runtime`.
