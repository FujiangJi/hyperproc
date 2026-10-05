# hyperproc.spectral._smoothspline._brent_fmin

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _brent_fmin(f, ax, bx, tol, eps, maxit)
```

Brent's golden-section plus parabolic search, as transcribed in sbart.c.

Returns ``(best, last_evaluated)``. Both are needed because R reports the
first and fits at the second.

Not replaced by a root find on purpose. R stops once ``spar`` is known to
about ``tol``, so its answer carries that error; solving exactly would be
more accurate and would not reproduce the published numbers.

[Module and aliases](../hyperproc-spectral-_smoothspline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral._smoothspline._brent_fmin --runtime`.
