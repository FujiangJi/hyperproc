# hyperproc.atmos.process._ortho_emit

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _ortho_emit(ds: xr.Dataset, source: Path, window: dict | None=None) -> xr.Dataset
```

Put a sensor-grid EMIT result on the granule's ortho grid through its GLT.

Lazy: the cube is gathered tile by tile when written. With ``window`` the
GLT is shifted to the window's origin and the ortho grid is cropped to the
cells the window covers.

[Module and aliases](../hyperproc-atmos-process.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.process._ortho_emit --runtime`.
