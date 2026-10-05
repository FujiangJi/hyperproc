# hyperproc.readers.aviris._gain

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _gain(cube: Path, granule: str) -> np.ndarray | None
```

Classic radiance is ``DN / gain``; the sidecar holds one factor per band.

NG and AVIRIS-3 ship float radiance already in uW nm-1 cm-2 sr-1 and have
no gain file, so this returns None for them.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._gain --runtime`.
