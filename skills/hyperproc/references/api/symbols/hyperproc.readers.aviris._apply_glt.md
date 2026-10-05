# hyperproc.readers.aviris._apply_glt

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _apply_glt(raw: np.ndarray, sample: np.ndarray, line: np.ndarray) -> np.ndarray
```

Put a raw ``(line, sample)`` layer onto the ortho grid.

JPL's lookup tables are 1-based with 0 for "no data", and a negative index
marks a cell filled from a neighbour rather than sampled directly. Both
signs point at a real pixel, so only the zeros are dropped.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._apply_glt --runtime`.
