# hyperproc.spectral._smoothspline._gram

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _gram(knot: np.ndarray) -> np.ndarray
```

``Sigma[i, j] = integral B''_i B''_j``, exactly as R's ``sgram.f`` computes it.

A cubic B-spline's second derivative is piecewise linear, so the integral of
a product over one knot interval has the closed form
``w * (a*c + (a*d + b*c)/2 + b*d/3)``. R writes that last coefficient as the
literal **0.3330**, not 1/3, and has done since the original Fortran.

That looks like a rounding of no consequence and is not: it shifts the
penalty by about 1e-3 relative, which moves ``ratio = tr(X'WX)/tr(Sigma)``
by the same amount and therefore moves ``lambda``. Integrating exactly, by
Gauss-Legendre, is the more correct thing to do and disagrees with R in the
third decimal of the fitted spectrum. Reproducing R means reproducing this.

[Module and aliases](../hyperproc-spectral-_smoothspline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral._smoothspline._gram --runtime`.
