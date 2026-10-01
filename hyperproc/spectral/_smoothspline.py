"""A faithful port of R's ``stats::smooth.spline``, for reproducing R pipelines.

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
"""
from __future__ import annotations

import numpy as np

__all__ = ["SmoothSpline", "smooth_spline", "nknots_smspl"]

_GOLD = 0.381966011250105151795413165634      # (3 - sqrt(5)) / 2
_BIG = 1e100


def nknots_smspl(n: int) -> int:
    """R's ``.nknots.smspl``: how many interior knots for ``n`` unique points."""
    if n < 50:
        return int(n)
    a1, a2, a3, a4 = np.log2(50.0), np.log2(100.0), np.log2(140.0), np.log2(200.0)
    if n < 200:
        v = 2.0 ** (a1 + (a2 - a1) * (n - 50) / 150.0)
    elif n < 800:
        v = 2.0 ** (a2 + (a3 - a2) * (n - 200) / 600.0)
    elif n < 3200:
        v = 2.0 ** (a3 + (a4 - a3) * (n - 800) / 2400.0)
    else:
        v = 200.0 + (n - 3200.0) ** 0.2
    return int(np.trunc(v))


def _iqr(x: np.ndarray) -> float:
    """R's ``IQR``, which uses quantile type 7 (numpy's default)."""
    q1, q3 = np.percentile(np.asarray(x, dtype="float64"), [25.0, 75.0])
    return float(q3 - q1)


def _collapse(x, y, w, tol):
    """De-duplicate x to a tolerance, averaging y as R does, and sort."""
    x = np.asarray(x, dtype="float64")
    y = np.asarray(y, dtype="float64")
    n = x.size
    w = np.ones(n) if w is None else np.asarray(w, dtype="float64") * (np.sum(np.asarray(w) > 0) / np.sum(w))
    xx = np.round((x - x.mean()) / tol)
    order = np.argsort(x, kind="stable")
    xs, xxs = x[order], xx[order]
    keep = np.concatenate([[True], xxs[1:] > xxs[:-1]])
    ux = xs[keep]
    group = np.cumsum(keep) - 1
    nx = ux.size
    wbar = np.bincount(group, weights=w[order], minlength=nx)
    ysum = np.bincount(group, weights=(w * y)[order], minlength=nx)
    ybar = np.where(wbar > 0, ysum / np.where(wbar > 0, wbar, 1.0), 0.0)
    return ux, ybar, wbar


def _knot_vector(xbar: np.ndarray, nknots: int) -> np.ndarray:
    """``c(rep(xbar[1],3), xbar[seq(1, nx, length.out=nknots)], rep(xbar[nx],3))``.

    R indexes with the raw doubles from ``seq.int``, and indexing with a double
    truncates, so the interior knots are at truncated positions, not rounded.
    """
    nx = xbar.size
    idx = np.trunc(np.linspace(1.0, float(nx), nknots)).astype(int) - 1
    return np.concatenate([np.repeat(xbar[0], 3), xbar[idx], np.repeat(xbar[-1], 3)])


def _basis(xbar: np.ndarray, knot: np.ndarray) -> np.ndarray:
    from scipy.interpolate import BSpline
    nk = knot.size - 4
    X = np.zeros((xbar.size, nk), dtype="float64")
    eye = np.eye(nk)
    for j in range(nk):
        X[:, j] = BSpline(knot, eye[j], 3, extrapolate=False)(xbar)
    return np.nan_to_num(X, nan=0.0)


def _gram(knot: np.ndarray) -> np.ndarray:
    """``Sigma[i, j] = integral B''_i B''_j``, exactly as R's ``sgram.f`` computes it.

    A cubic B-spline's second derivative is piecewise linear, so the integral of
    a product over one knot interval has the closed form
    ``w * (a*c + (a*d + b*c)/2 + b*d/3)``. R writes that last coefficient as the
    literal **0.3330**, not 1/3, and has done since the original Fortran.

    That looks like a rounding of no consequence and is not: it shifts the
    penalty by about 1e-3 relative, which moves ``ratio = tr(X'WX)/tr(Sigma)``
    by the same amount and therefore moves ``lambda``. Integrating exactly, by
    Gauss-Legendre, is the more correct thing to do and disagrees with R in the
    third decimal of the fitted spectrum. Reproducing R means reproducing this.
    """
    from scipy.interpolate import BSpline
    nk = knot.size - 4
    sigma = np.zeros((nk, nk), dtype="float64")
    eye = np.eye(nk)
    d2 = [BSpline(knot, eye[j], 3, extrapolate=False).derivative(2) for j in range(nk)]

    for i in range(nk):
        a, b = knot[i], knot[i + 1]
        wpt = b - a
        if wpt <= 0:
            continue
        # the four basis functions supported on this interval
        j0 = i - 3
        cols = [j for j in range(max(0, j0), min(nk, j0 + 4))]
        if not cols:
            continue
        # B'' is linear here, so two interior samples give the endpoints exactly
        x1, x2 = a + wpt / 3.0, a + 2.0 * wpt / 3.0
        f1 = np.array([np.nan_to_num(d2[j](x1), nan=0.0) for j in cols], dtype="float64")
        f2 = np.array([np.nan_to_num(d2[j](x2), nan=0.0) for j in cols], dtype="float64")
        yw1 = 2.0 * f1 - f2                    # value at the left end
        yw2 = (2.0 * f2 - f1) - yw1            # increment across the interval
        block = wpt * (np.outer(yw1, yw1)
                       + 0.5 * (np.outer(yw2, yw1) + np.outer(yw1, yw2))
                       + 0.3330 * np.outer(yw2, yw2))
        sigma[np.ix_(cols, cols)] += block
    return sigma


def _solve(X, sigma, wbar, ybar, lam):
    """Fit at one lambda; return coefficients, fitted values and leverages."""
    XtW = X.T * wbar[None, :]
    A = XtW @ X + lam * sigma
    rhs = XtW @ ybar
    coef = np.linalg.solve(A, rhs)
    fitted = X @ coef
    lev = wbar * np.einsum("ij,ji->i", X, np.linalg.solve(A, X.T))
    return coef, fitted, lev


class SmoothSpline:
    """The fitted spline, with R's own diagnostics on it.

    Attributes mirror R's object: ``df`` (the achieved trace, not the target),
    ``lambda_``, ``spar``, ``nknots`` and ``coef``.
    """

    def __init__(self, x, y, df=None, spar=None, lam=None, w=None,
                 tol=None, nknots=None, maxit=500, search_tol=1e-4, eps=2e-8):
        x = np.asarray(x, dtype="float64")
        y = np.asarray(y, dtype="float64")
        if not (np.isfinite(x).all() and np.isfinite(y).all()):
            raise ValueError("missing or infinite values in inputs are not allowed")
        tol = 1e-6 * _iqr(x) if tol is None else float(tol)
        if not np.isfinite(tol) or tol <= 0:
            raise ValueError("'tol' must be strictly positive and finite")
        ux, ybar, wbar = _collapse(x, y, w, tol)
        nx = ux.size
        if nx <= 3:
            raise ValueError("need at least four unique 'x' values")
        self.x_min, self.x_range = float(ux[0]), float(ux[-1] - ux[0])
        xbar = (ux - ux[0]) / self.x_range

        nknots = nknots_smspl(nx) if nknots is None else int(nknots)
        if not 1 <= nknots <= nx:
            raise ValueError(f"nknots must be in 1..{nx}; got {nknots}")
        self.knot = _knot_vector(xbar, nknots)
        self.nknots = nknots
        X, sigma = _basis(xbar, self.knot), _gram(self.knot)
        nk = X.shape[1]

        diag_xwx = np.einsum("ij,i,ij->j", X, wbar, X)
        ratio = float(diag_xwx[2:nk - 3].sum() / np.diag(sigma)[2:nk - 3].sum())
        self.ratio = ratio

        def at_spar(s):
            lam_ = ratio * 16.0 ** (6.0 * s - 2.0)
            coef, fitted, lev = _solve(X, sigma, wbar, ybar, lam_)
            return lam_, coef, fitted, lev

        if lam is not None:
            self.spar = np.nan
            self.lambda_ = float(lam)
            self.coef, self._fitted, lev = _solve(X, sigma, wbar, ybar, self.lambda_)
        elif spar is not None:
            self.spar = float(spar)
            self.lambda_, self.coef, self._fitted, lev = at_spar(self.spar)
        else:
            if df is None:
                raise ValueError("give one of df=, spar= or lam=")
            if not 1 < df <= nx:
                raise ValueError(f"invalid df; must have 1 < df <= {nx}")

            def crit(s):
                _, _, _, lev_ = at_spar(s)
                return 3.0 + (df - lev_.sum()) ** 2

            # R returns the coefficients, lambda and leverages of the LAST trial
            # evaluation, not of the spar it reports: sbart.c never recomputes the fit
            # at the optimum before returning. Reproducing R's spectrum means
            # reproducing that, so the search hands back both points.
            self.spar, last = _brent_fmin(crit, -1.5, 1.5, search_tol, eps, maxit)
            self.spar_used = last
            self.lambda_, self.coef, self._fitted, lev = at_spar(last)
        self.lev = lev
        self.df = float(lev.sum())
        self.x, self.y = ux, ybar

    def predict(self, x) -> np.ndarray:
        """Evaluate the spline, extrapolating linearly as a natural spline does."""
        from scipy.interpolate import BSpline
        x = np.atleast_1d(np.asarray(x, dtype="float64"))
        t = (x - self.x_min) / self.x_range
        spline = BSpline(self.knot, self.coef, 3, extrapolate=False)
        out = spline(np.clip(t, 0.0, 1.0))
        out = np.nan_to_num(out, nan=0.0)
        low, high = t < 0.0, t > 1.0
        if low.any() or high.any():
            d1 = spline.derivative(1)
            if low.any():
                out[low] = spline(0.0) + d1(0.0) * (t[low] - 0.0)
            if high.any():
                out[high] = spline(1.0) + d1(1.0) * (t[high] - 1.0)
        return out


def _brent_fmin(f, ax, bx, tol, eps, maxit):
    """Brent's golden-section plus parabolic search, as transcribed in sbart.c.

    Returns ``(best, last_evaluated)``. Both are needed because R reports the
    first and fits at the second.

    Not replaced by a root find on purpose. R stops once ``spar`` is known to
    about ``tol``, so its answer carries that error; solving exactly would be
    more accurate and would not reproduce the published numbers.
    """
    a, b = float(ax), float(bx)
    v = a + _GOLD * (b - a)
    w = x = last_u = v
    e = d = 0.0
    fx = f(x)
    fv = fw = fx
    for _ in range(int(maxit)):
        xm = (a + b) * 0.5
        tol1 = eps * abs(x) + tol / 3.0
        tol2 = tol1 * 2.0
        if abs(x - xm) <= tol2 - (b - a) * 0.5:
            break
        golden = True
        if abs(e) > tol1 and fx < _BIG and fv < _BIG and fw < _BIG:
            r = (x - w) * (fx - fv)
            q = (x - v) * (fx - fw)
            p = (x - v) * q - (x - w) * r
            q = (q - r) * 2.0
            if q > 0.0:
                p = -p
            q = abs(q)
            r, e = e, d
            if abs(p) < abs(0.5 * q * r) and q != 0.0 and q * (a - x) < p < q * (b - x):
                d = p / q
                u = x + d
                if u - a < tol2 or b - u < tol2:
                    d = abs(tol1) if xm - x >= 0 else -abs(tol1)
                golden = False
        if golden:
            e = (a - x) if x >= xm else (b - x)
            d = _GOLD * e
        u = x + (d if abs(d) >= tol1 else (abs(tol1) if d >= 0 else -abs(tol1)))
        fu = f(u)
        if not np.isfinite(fu):
            fu = 2.0 * _BIG
        last_u = u
        if fu <= fx:
            if u >= x:
                a = x
            else:
                b = x
            v, fv, w, fw, x, fx = w, fw, x, fx, u, fu
        else:
            if u < x:
                a = u
            else:
                b = u
            if fu <= fw or w == x:
                v, fv, w, fw = w, fw, u, fu
            elif fu <= fv or v == x or v == w:
                v, fv = u, fu
    return x, last_u


def smooth_spline(x, y, df=None, spar=None, lam=None, **kw) -> SmoothSpline:
    """R's ``smooth.spline``. See :class:`SmoothSpline`."""
    return SmoothSpline(x, y, df=df, spar=spar, lam=lam, **kw)
