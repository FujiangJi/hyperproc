# hyperproc.correct.mcd43._download

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _download(ee, img, bands: list, transform: tuple, nx: int, ny: int, fill: int, tile: int=TILE, verbose: bool=True, retries: int=4) -> np.ndarray
```

Pull a pinned grid out of Earth Engine, tile by tile, as ``(ny, nx, nband)``.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43._download --runtime`.
