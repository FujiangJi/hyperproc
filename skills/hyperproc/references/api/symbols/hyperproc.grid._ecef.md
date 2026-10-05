# hyperproc.grid._ecef

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _ecef(lat: np.ndarray, lon: np.ndarray) -> np.ndarray
```

Sphere-surface cartesian metres, so a KD-tree measures real distance.

Doing the search in degrees would distort badly over a swath spanning 23
degrees of latitude, where a degree of longitude shrinks by a third.

[Module and aliases](../hyperproc-grid.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.grid._ecef --runtime`.
