# hyperproc.spectral._smoothspline._knot_vector

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _knot_vector(xbar: np.ndarray, nknots: int) -> np.ndarray
```

``c(rep(xbar[1],3), xbar[seq(1, nx, length.out=nknots)], rep(xbar[nx],3))``.

R indexes with the raw doubles from ``seq.int``, and indexing with a double
truncates, so the interior knots are at truncated positions, not rounded.

[Module and aliases](../hyperproc-spectral-_smoothspline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral._smoothspline._knot_vector --runtime`.
