# hyperproc.grid.latlon_grid

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def latlon_grid(ds: xr.Dataset) -> tuple[np.ndarray, np.ndarray]
```

WGS-84 ``(lat, lon)`` of every cell centre of a projected dataset.

Derived from the CRS and the full affine transform, so it is exact even
where the granule ships no geolocation arrays - including the rotated,
flight-aligned AVIRIS grids, where the 1-D ``x``/``y`` coordinates describe
only the top row and left column. The affine is rebuilt from the
coordinates the same way the GeoTIFF writer does, so subsets stay right.

[Module and aliases](../hyperproc-grid.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.grid.latlon_grid --runtime`.
