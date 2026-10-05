# hyperproc.atmos.dem.sample

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def sample(lat, lon, resolution: int=30, fallback: bool=True, verbose: bool=False) -> np.ndarray
```

Elevation (m above EGM2008) at every (lat, lon), bilinear within each tile.

NaN where the coordinates are not finite; 0 where no tile exists (sea).

[Module and aliases](../hyperproc-atmos-dem.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.dem.sample --runtime`.
