# hyperproc.align._prepare

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _prepare(a: np.ndarray) -> np.ndarray
```

Mean-removed, NaN-filled and windowed, ready for an FFT.

The Hann window matters: an image is not periodic, and without it the
discontinuity at the wrap-around produces a cross-shaped artefact through
the correlation surface that can outrank the real peak.

[Module and aliases](../hyperproc-align.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.align._prepare --runtime`.
