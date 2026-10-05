# hyperproc.io._spatial_da

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _spatial_da(arr: np.ndarray, ds: xr.Dataset, projected: bool)
```

Wrap a (band, y, x) array, carrying the dataset's grid so the GeoTIFF
gets a real transform. Without the coords rioxarray writes the identity
matrix and the raster lands at the CRS origin instead of the scene.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io._spatial_da --runtime`.
