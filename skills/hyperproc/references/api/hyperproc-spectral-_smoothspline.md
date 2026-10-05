# hyperproc.spectral._smoothspline

Release baseline **0.1.2**; source `hyperproc/spectral/_smoothspline.py`. Choose a callable below rather than loading every declaration.

A faithful port of R's ``stats::smooth.spline``, for reproducing R pipelines.

Published spectroscopy workflows are often written in R, and a Python package
that wants to reproduce their numbers has to reproduce their smoother, not
merely a smoother. ``scipy``'s ``UnivariateSpline`` is a different algorithm
with a different parameterisation, so it cannot: it would give plausible
answers that do not match.

This follows R's implementation step for step, from ``src/library/stats``:

* ``.nknots.smspl`` chooses the number of interior knots (``smspline.R``).
* ``x`` is de-meaned, rounded to a tolerance of ``1e-6 * IQR(x)`` and
  de-duplicated, then scaled to the unit interval.
* knots are taken at ``xbar[trunc(seq(1, nx, length.out = nknots))]`` with the
  end knots repeated three times, giving ``nknots + 2`` cubic B-splines.
* the penalty is the Gram matrix of the basis second derivatives, computed
  exactly: a cubic B-spline's second derivative is piecewise linear, so the
  product is piecewise quadratic and three-point Gauss-Legendre is exact.
* the smoothing parameter enters as ``lambda = ratio * 16^(6*spar - 2)`` with
  ``ratio = tr(X'WX) / tr(Sigma)`` over the interior band (``sbart.c``).
* ``df`` is matched by minimising ``3 + (df - tr(H))^2`` over ``spar`` in
  ``[-1.5, 1.5]``, using Brent's golden-section and parabolic search with
  R's own constants (``tol = 1e-4``, ``eps = 2e-8``, 500 iterations).

That last point is why the search is transcribed rather than replaced by a
root find. R stops when ``spar`` is known to about 1e-4, so its ``df`` lands
near 59.995 rather than 60. An exact solver would be more accurate and would
not match. Reproducing the published number means reproducing the search.

## Declared exports

`SmoothSpline`, `smooth_spline`, `nknots_smspl`

## Declared callables and classes

- [nknots_smspl](symbols/hyperproc.spectral._smoothspline.nknots_smspl.md) — internal
- [_iqr](symbols/hyperproc.spectral._smoothspline._iqr.md) — internal
- [_collapse](symbols/hyperproc.spectral._smoothspline._collapse.md) — internal
- [_knot_vector](symbols/hyperproc.spectral._smoothspline._knot_vector.md) — internal
- [_basis](symbols/hyperproc.spectral._smoothspline._basis.md) — internal
- [_gram](symbols/hyperproc.spectral._smoothspline._gram.md) — internal
- [_solve](symbols/hyperproc.spectral._smoothspline._solve.md) — internal
- [_brent_fmin](symbols/hyperproc.spectral._smoothspline._brent_fmin.md) — internal
- [smooth_spline](symbols/hyperproc.spectral._smoothspline.smooth_spline.md) — internal
- [SmoothSpline](symbols/hyperproc.spectral._smoothspline.SmoothSpline.md)

## Constant expressions

- [_GOLD](constants/hyperproc.spectral._smoothspline._GOLD.md)
- [_BIG](constants/hyperproc.spectral._smoothspline._BIG.md)
