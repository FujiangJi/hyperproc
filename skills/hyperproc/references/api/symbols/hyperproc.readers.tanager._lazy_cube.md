# hyperproc.readers.tanager._lazy_cube

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _lazy_cube(raw: xr.DataArray, bi: np.ndarray) -> xr.DataArray
```

(band, y, x) on disk -> lazy (y, x, wavelength) float32 with FILL as NaN.

[Module and aliases](../hyperproc-readers-tanager.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.tanager._lazy_cube --runtime`.
