# hyperproc.spectral.continuum._upper_hull

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _upper_hull(a: np.ndarray, wl: np.ndarray) -> np.ndarray
```

Upper convex hull of each spectrum, evaluated at every wavelength.

A monotone chain, run for every pixel at once: the stack is an index array
and the "pop" step is a masked update, so the cost is a few hundred
vector operations rather than a Python loop over millions of spectra.

[Module and aliases](../hyperproc-spectral-continuum.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.continuum._upper_hull --runtime`.
