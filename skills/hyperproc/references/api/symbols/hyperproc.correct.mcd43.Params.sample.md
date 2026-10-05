# hyperproc.correct.mcd43.Params.sample

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def sample(self, lon, lat, method: str='bilinear') -> np.ndarray
```

Parameters at scattered points, shape ``lon.shape + (7, 3)``.

Sampling the parameters (rather than warping them to the image grid and
reading back) keeps one code path for projected images and for swaths,
where every pixel has its own longitude and latitude.

NaN cells are skipped and the remaining bilinear weights renormalised,
so a point next to a gap still gets a value; a point whose four
neighbours are all fill comes back NaN.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.Params.sample --runtime`.
