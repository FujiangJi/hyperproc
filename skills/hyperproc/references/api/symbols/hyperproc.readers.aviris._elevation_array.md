# hyperproc.readers.aviris._elevation_array

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _elevation_array(src: str, band: int, glt: str | None, stamp: tuple, ny: int, nx: int) -> np.ndarray | None
```

Decorators: `functools.lru_cache(maxsize=4)`.

Read (and if needed orthorectify) a DEM, remembering the last few.

Reading it eagerly is what makes :func:`check_geometry` possible, but a
notebook opens the same granule repeatedly and each open was re-reading
0.2-0.5 GB and redoing the GLT gather. Four entries is 40-115 MB each
depending on grid, so at most a few hundred MB held against opens that
would otherwise cost seconds apiece.

``stamp`` is the source file's (mtime, size); it is in the key so an
edited or replaced sidecar is not served from a stale entry.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._elevation_array --runtime`.
