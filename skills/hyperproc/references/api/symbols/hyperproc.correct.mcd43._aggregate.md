# hyperproc.correct.mcd43._aggregate

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _aggregate(ee, img, k: int, transform: tuple, reducer: str='mean')
```

Average ``k x k`` native MODIS cells into one output cell.

Done on the *masked* image, so cells with no retrieval never contribute to
the mean; the caller unmasks to the fill value afterwards. Point-sampling a
500 m field at kilometre spacing would alias instead, which is why this
exists at all (PACE OCI is the sensor that needs it).

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43._aggregate --runtime`.
