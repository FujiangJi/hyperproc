# hyperproc.align._to_metres

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _to_metres(dy_map: float, dx_map: float, crs: str, reference: xr.Dataset) -> tuple
```

Map units to metres on the ground.

A projected grid is already in metres; a geographic one is in degrees, and
reporting "0.0 degrees" for a shift of three EMIT pixels tells nobody
anything. Longitude shrinks by cos(latitude), so the scene's own latitude
is used rather than a constant.

[Module and aliases](../hyperproc-align.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.align._to_metres --runtime`.
