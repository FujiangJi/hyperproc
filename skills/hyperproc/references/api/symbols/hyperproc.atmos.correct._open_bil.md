# hyperproc.atmos.correct._open_bil

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _open_bil(path: Path, chunks_rows: int | None=None) -> xr.DataArray
```

Lazy ``(band, y, x)`` view of an ENVI file, FILL -> NaN, float32.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct._open_bil --runtime`.
