# hyperproc.readers.enmap._add_pixelmask

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _add_pixelmask(ds: xr.Dataset, path: Path, stem: str, level: str, bidx: np.ndarray, n_vnir: int) -> None
```

Per-band pixel mask, lazily, on the cube's own band axis.

The mask file has one band per spectral band of the *file* it belongs to,
so the cube's source band positions (``bidx``) index it directly at
L1C/L2A; at L1B only the opened detector's mask applies, and the SWIR
positions are offset by the VNIR band count.

[Module and aliases](../hyperproc-readers-enmap.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.enmap._add_pixelmask --runtime`.
