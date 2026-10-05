# hyperproc.readers.enmap._footprint_grid

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _footprint_grid(c: dict, corners, ny: int, nx: int) -> np.ndarray
```

Plane through the four footprint-corner values, NaN outside the footprint.

Corner angles vary linearly across a scene to well under 0.1 deg, so a
least-squares plane on (col, row) reproduces the given corner values and,
unlike a bilinear fill of the raster box, puts them where the footprint
corners actually are (0.55 deg error at the corners otherwise).

[Module and aliases](../hyperproc-readers-enmap.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.enmap._footprint_grid --runtime`.
