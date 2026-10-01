"""Topographic (illumination) correction: cosine, C, SCS and SCS+C.

Written from the primary sources:

* Teillet, Guindon & Goodenough (1982) - the cosine correction and the
  C-correction, with C the ratio of intercept to slope of the regression of
  reflectance on the cosine of the solar incidence angle.
* Gu & Gillespie (1998) - the sun-canopy-sensor (SCS) correction.
* Soenen, Peddle & Coburn (2005) - SCS+C, eqs 7-8: C fitted exactly as in
  Teillet, then added to both numerator and denominator of SCS.

The cosine of the local solar incidence angle is

    cos i = cos(slope) cos(sza) + sin(slope) sin(sza) cos(saa - aspect)

and the four corrections are multiplicative factors on reflectance:

    cosine   rho * cos(sza)                 / cos i
    c        rho * (cos(sza) + C)           / (cos i + C)
    scs      rho * cos(slope) cos(sza)      / cos i
    scs+c    rho * (cos(slope) cos(sza) + C)/ (cos i + C)

Two deliberate departures from other implementations:

1. **No sentinel.** A common shortcut is to return ``C = 100000`` when the
   regression slope is zero (or clamped to zero by NNLS), which makes the
   factor 1 and silently leaves the band uncorrected. Here :func:`fit_c` returns ``C = None`` with a
   ``status`` that says *why* - ``insufficient``, ``degenerate`` (no usable
   illumination contrast) or ``inverted`` (reflectance *falls* with cos i, as
   AVIRIS-5 L2A_OE does) - and :func:`apply_topo` refuses a band without a C.
2. **The decision is measured, not assumed.** :func:`illumination_diagnostic`
   reports, per band, how strongly reflectance still depends on cos i in the
   product as delivered, and how strongly it would after correction, on
   held-out pixels. That is what ``fix_topo="auto"`` acts on.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

METHODS = ("cosine", "c", "scs", "scs+c")


def cos_incidence(sza, saa, slope, aspect):
    """cos i from solar zenith/azimuth and terrain slope/aspect, all in radians.

    Azimuths need only be in a common convention (both clockwise from north);
    the difference is all that enters.
    """
    return (np.cos(slope) * np.cos(sza)
            + np.sin(slope) * np.sin(sza) * np.cos(saa - aspect))


@dataclass
class CFit:
    """Result of regressing reflectance on cos i for one band."""

    slope: float | None        # a in rho = a cos i + b
    intercept: float | None    # b
    c: float | None            # b / a, or None when it should not be used
    r: float | None            # Pearson correlation of rho with cos i
    n: int                     # samples used
    cos_i_spread: float        # std of cos i in the sample - the illumination contrast
    status: str                # ok | insufficient | degenerate | inverted | negative_intercept
    method: str                # ols | nnls
    effect: float | None = None   # a (p95 - p05 of cos i) / mean rho: illumination-driven change as a fraction of the mean
    t: float | None = None        # OLS slope over its standard error - the dependence's significance

    def as_dict(self):
        return asdict(self)


def fit_c(rho, cos_i, method="ols", min_samples=100, min_spread=0.02, neg_tol=0.05):
    """Fit C = intercept / slope of ``rho = a cos_i + b`` (Teillet 1982; Soenen 2005 eq 7-8).

    Args:
        rho, cos_i: 1-D samples, already masked to the pixels you trust
            (vegetated, sloped, illuminated).
        method: ``"ols"`` or ``"nnls"``. NNLS clamps a negative slope to zero;
            rather than turn that into a huge C (the usual 100000 sentinel) the
            fit is reported as ``inverted`` and C is None.
        neg_tol: an OLS intercept more negative than ``neg_tol`` x mean
            reflectance (and significant, t < -2) is an additive offset in the
            product: status ``negative_intercept``, no C, under either method.
        min_samples: fewer than this -> ``insufficient``.
        min_spread: std of cos i below this -> ``degenerate`` - on flat ground
            there is no illumination contrast to regress against, and any C
            is noise. (A flat scene fits the same C in every band for exactly
            this reason.)

    The correlation ``r`` is reported but never used to judge the fit: over a
    whole flightline most reflectance variance is land cover, so r is tiny
    (0.03 on a NEON line) while the illumination effect is large (11% of the
    mean at 659 nm). Judge with ``effect`` - the change in reflectance across
    the central 90% of the illumination range, as a fraction of the mean -
    and ``t``, the slope's significance; :func:`illumination_diagnostic` does.

    Returns:
        :class:`CFit`. ``c`` is only set when ``status == "ok"``.
    """
    rho = np.asarray(rho, dtype="float64").ravel()
    ci = np.asarray(cos_i, dtype="float64").ravel()
    good = np.isfinite(rho) & np.isfinite(ci)
    rho, ci = rho[good], ci[good]
    n = int(rho.size)
    if n < min_samples:
        return CFit(None, None, None, None, n, float(np.std(ci)) if n else 0.0,
                    "insufficient", method)
    spread = float(np.std(ci))
    if spread < min_spread:
        return CFit(None, None, None, None, n, spread, "degenerate", method)

    X = np.column_stack([ci, np.ones_like(ci)])
    (a_ols, b_ols), *_ = np.linalg.lstsq(X, rho, rcond=None)
    if method == "nnls":
        from scipy.optimize import nnls
        (a, b), _ = nnls(X, rho)
    elif method == "ols":
        a, b = a_ols, b_ols
    else:
        raise ValueError(f"method must be 'ols' or 'nnls', not {method!r}")
    r = float(np.corrcoef(ci, rho)[0, 1])
    resid = rho - (a_ols * ci + b_ols)
    sxx = ((ci - ci.mean()) ** 2).sum()
    s2 = resid @ resid / max(n - 2, 1)
    se = float(np.sqrt(s2 / sxx))
    t = float(a_ols / se) if se > 0 else None
    se_b = float(np.sqrt(s2 * (1.0 / n + ci.mean() ** 2 / sxx)))
    t_b = float(b_ols / se_b) if se_b > 0 else 0.0
    lo, hi = np.percentile(ci, [5, 95])
    mean = float(rho.mean())
    effect = float(a * (hi - lo) / mean) if mean > 0 else None

    if not np.isfinite(a) or a <= 0:
        # Reflectance falls (or does not rise) with illumination: the product
        # has already been over-compensated, or something else dominates.
        # SCS+C would make it worse, so no C is offered.
        return CFit(float(a), float(b), None, r, n, spread, "inverted", method, effect, t)
    if b_ols < -neg_tol * mean and t_b < -2.0:
        # A materially negative intercept (more than neg_tol of the mean
        # reflectance, and significant) means reflectance would reach zero at a
        # clearly positive cos i: an additive offset in the product (path-
        # radiance residuals in the blue, for instance), not an illumination
        # model. Under OLS C = b/a would be negative and the factor singular;
        # under NNLS the intercept is clamped to 0 and a pure SCS factor then
        # amplifies the offset and the noise several-fold in shadow - both are
        # damage, so no C. A small negative intercept (within neg_tol) becomes
        # C = 0 (SCS) under NNLS, and is refused under OLS.
        return CFit(float(a), float(b), None, r, n, spread, "negative_intercept", method, effect, t)
    if b < 0:
        return CFit(float(a), float(b), None, r, n, spread, "negative_intercept", method, effect, t)
    return CFit(float(a), float(b), float(b / a), r, n, spread, "ok", method, effect, t)


def fit_c_from_sums(n, sx, sy, sxy, sxx, syy, cos_i_p05, cos_i_p95, method="ols", min_samples=100,
                    min_spread=0.02, neg_tol=0.05):
    """:func:`fit_c` from per-band regression sums over *all* masked pixels of an
    image, accumulated while the cube streams past - so the topographic C is
    fitted on every pixel of the calc mask without holding the cube in memory.

    ``n, sx, sy, sxy, sxx, syy`` are the counts and sums of cos i (x) and
    reflectance (y) over the mask; ``cos_i_p05/p95`` the illumination range
    the effect size is expressed over. With two parameters the NNLS solution
    is exact in closed form: the unconstrained fit when both coefficients are
    non-negative, otherwise the better of the two boundary fits (b = 0 or a = 0).
    Statuses are the same as :func:`fit_c`.
    """
    n = int(n)
    if n < min_samples:
        return CFit(None, None, None, None, n, 0.0, "insufficient", method)
    mx, my = sx / n, sy / n
    sxx_c = sxx - n * mx * mx; syy_c = syy - n * my * my; sxy_c = sxy - n * mx * my
    spread = float(np.sqrt(max(sxx_c, 0.0) / n))
    if spread < min_spread or sxx_c <= 0:
        return CFit(None, None, None, None, n, spread, "degenerate", method)
    a_ols = sxy_c / sxx_c; b_ols = my - a_ols * mx
    r = float(sxy_c / np.sqrt(sxx_c * syy_c)) if syy_c > 0 else 0.0
    sse = max(syy - a_ols * sxy - b_ols * sy, 0.0)                   # residual sum of squares of the OLS fit
    s2 = sse / max(n - 2, 1)
    se = float(np.sqrt(s2 / sxx_c)); t = float(a_ols / se) if se > 0 else None
    se_b = float(np.sqrt(s2 * (1.0 / n + mx * mx / sxx_c))); t_b = float(b_ols / se_b) if se_b > 0 else 0.0
    if method == "nnls":
        if a_ols >= 0 and b_ols >= 0:
            a, b = a_ols, b_ols
        else:
            cands = []
            a1 = max(sxy / sxx, 0.0) if sxx > 0 else 0.0            # b = 0
            cands.append((syy - 2 * a1 * sxy + a1 * a1 * sxx, a1, 0.0))
            b2 = max(my, 0.0)                                        # a = 0
            cands.append((syy - 2 * b2 * sy + n * b2 * b2, 0.0, b2))
            _, a, b = min(cands, key=lambda c: c[0])
    elif method == "ols":
        a, b = a_ols, b_ols
    else:
        raise ValueError(f"method must be 'ols' or 'nnls', not {method!r}")
    effect = float(a * (cos_i_p95 - cos_i_p05) / my) if my > 0 else None
    if not np.isfinite(a) or a <= 0:
        return CFit(float(a), float(b), None, r, n, spread, "inverted", method, effect, t)
    if b_ols < -neg_tol * my and t_b < -2.0:
        return CFit(float(a), float(b), None, r, n, spread, "negative_intercept", method, effect, t)
    if b < 0:
        return CFit(float(a), float(b), None, r, n, spread, "negative_intercept", method, effect, t)
    return CFit(float(a), float(b), float(b / a), r, n, spread, "ok", method, effect, t)


def _check_c(c):
    """Any C must be finite and >= 0: a negative C makes the SCS+C / C factor
    singular inside the valid cos i range."""
    vals = np.asarray([v for v in (c if isinstance(c, (list, tuple, np.ndarray)) else [c]) if v is not None], dtype=float)
    if vals.size and (~np.isfinite(vals) | (vals < 0)).any():
        raise ValueError("C must be finite and >= 0 for every band; a negative C (negative regression intercept) is not "
                         "a valid topographic model - fit with method='nnls' or drop the band")


def correction_factor(method, cos_i, sza, slope=None, c=None):
    """The multiplicative factor for one of :data:`METHODS`. Radians in, factor out.

    ``c`` may be a scalar or an array broadcastable against ``cos_i`` (one C per
    band, with a trailing band axis, is the usual case).
    """
    if c is not None:
        _check_c(c)
    if method == "cosine":
        return np.cos(sza) / cos_i
    if method == "scs":
        return np.cos(slope) * np.cos(sza) / cos_i
    if c is None:
        raise ValueError(f"{method!r} needs a C coefficient")
    if method == "c":
        return (np.cos(sza) + c) / (cos_i + c)
    if method == "scs+c":
        return (np.cos(slope) * np.cos(sza) + c) / (cos_i + c)
    raise ValueError(f"unknown method {method!r}; choose from {METHODS}")


def apply_topo(rho, cos_i, sza, slope=None, method="scs+c", c=None,
               mask=None, cos_i_min=0.0):
    """Apply a topographic correction to a ``(..., band)`` reflectance array.

    Args:
        rho: reflectance with the band axis last.
        cos_i, sza, slope: per-pixel arrays (radians for the angles) matching
            ``rho.shape[:-1]``.
        method: one of :data:`METHODS`.
        c: for ``"c"`` / ``"scs+c"``, an array of length ``rho.shape[-1]`` with
            one C per band, or None for bands that must not be corrected.
        mask: boolean ``rho.shape[:-1]``; False pixels are returned unchanged.
        cos_i_min: pixels with ``cos i`` at or below this are left unchanged
            (the factor blows up towards grazing incidence).

    Returns:
        Corrected array, float32, same shape. Bands whose C is None are
        returned unchanged - never silently "corrected" by a factor of 1
        dressed up as a result.
    """
    rho = np.asarray(rho, dtype="float32")
    out = rho.copy()
    keep = np.isfinite(cos_i) & (cos_i > cos_i_min)
    if mask is not None:
        keep &= mask
    if method in ("c", "scs+c"):
        c = np.asarray([np.nan if v is None else v for v in np.atleast_1d(c)], dtype="float64")
        if c.shape != (rho.shape[-1],):
            raise ValueError(f"c must have one entry per band ({rho.shape[-1]}), got {c.shape}")
        for k in range(rho.shape[-1]):
            if not np.isfinite(c[k]):
                continue
            f = correction_factor(method, cos_i, sza, slope, c[k])
            out[..., k] = np.where(keep, rho[..., k] * f, rho[..., k])
    else:
        f = correction_factor(method, cos_i, sza, slope)
        out = np.where(keep[..., None], rho * f[..., None], rho).astype("float32")
    return out


def _slope_stats(x, y):
    """OLS slope of y on x, its t statistic and Pearson r."""
    X = np.column_stack([x, np.ones_like(x)])
    (a, b), *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - (a * x + b)
    se = np.sqrt(resid @ resid / max(x.size - 2, 1) / ((x - x.mean()) ** 2).sum())
    return float(a), (float(a / se) if se > 0 else np.nan), float(np.corrcoef(x, y)[0, 1])


def illumination_diagnostic(rho, cos_i, sza, slope, mask, method="scs+c",
                            fit_method="ols", holdout=0.5, seed=0,
                            min_effect=0.01, t_threshold=3.0):
    """How much does reflectance still depend on illumination - and would a
    correction help? One row per band.

    Fits C on a random half of the masked pixels and evaluates on the other
    half with the least-squares slope of reflectance against cos i, expressed
    as ``effect`` = slope x (p95 - p05 of cos i) / mean reflectance: the
    illumination-driven change across the central 90% of the scene's
    illumination range, as a fraction of the mean - before correction and
    after. A correction that helps drives the held-out effect towards zero;
    one that hurts drives it negative or leaves it.

    Why not the correlation coefficient: over a whole flightline most of the
    reflectance variance is land cover, so r stays near zero (0.03 on a NEON
    line) even when the effect is 11% of the mean. r measures how *cleanly*
    reflectance follows illumination, not how *much*.

    Returns:
        dict with per-band arrays ``effect_before``, ``effect_after``,
        ``t_before`` (slope significance), ``r_before``, ``r_after`` (for
        information), ``c``, ``status``, the lit/shaded ``contrast`` (median
        rho at the top cos-i decile over the bottom decile, minus 1), and a
        scene-level ``verdict``: ``"correct"`` (a significant dependence of
        at least ``min_effect`` that the correction at least halves),
        ``"skip"`` (illumination varies but reflectance follows it by less
        than ``min_effect``, or not significantly - nothing worth correcting),
        ``"refuse"`` (significantly inverted - the correction would
        over-correct), or ``"inconclusive"`` (too little illumination
        contrast or too few pixels to tell either way).
    """
    rho = np.asarray(rho, dtype="float64")
    nb = rho.shape[-1]
    idx = np.flatnonzero(mask & np.isfinite(cos_i))
    rng = np.random.default_rng(seed)
    rng.shuffle(idx)
    fit_idx, test_idx = idx[: int(len(idx) * holdout)], idx[int(len(idx) * holdout):]
    flat = rho.reshape(-1, nb)
    ci = np.asarray(cos_i, dtype="float64").ravel()
    sz = np.asarray(sza, dtype="float64").ravel()
    sl = np.asarray(slope, dtype="float64").ravel()

    eff_b = np.full(nb, np.nan); eff_a = np.full(nb, np.nan); t_b = np.full(nb, np.nan)
    r_before = np.full(nb, np.nan); r_after = np.full(nb, np.nan)
    c_out = np.full(nb, np.nan); contrast = np.full(nb, np.nan)
    status = np.array(["insufficient"] * nb, dtype=object)
    ci_t = ci[test_idx]
    p05, p95 = (np.percentile(ci_t, [5, 95]) if test_idx.size else (np.nan, np.nan))
    lo, hi = (np.percentile(ci_t, [10, 90]) if test_idx.size else (np.nan, np.nan))
    for k in range(nb):
        y_fit = flat[fit_idx, k]; y_test = flat[test_idx, k]
        fit = fit_c(y_fit, ci[fit_idx], method=fit_method)
        status[k] = fit.status
        ok_t = np.isfinite(y_test)
        if ok_t.sum() > 30 and np.std(ci_t[ok_t]) > 0:
            a, t, r = _slope_stats(ci_t[ok_t], y_test[ok_t])
            mean = y_test[ok_t].mean()
            if mean > 0:
                eff_b[k] = a * (p95 - p05) / mean
            t_b[k] = t; r_before[k] = r
            shaded = y_test[ok_t & (ci_t < lo)]; lit = y_test[ok_t & (ci_t > hi)]
            if shaded.size and lit.size and np.median(shaded) > 0:
                contrast[k] = np.median(lit) / np.median(shaded) - 1.0
        if fit.status == "ok":
            c_out[k] = fit.c
            corr = apply_topo(y_test[:, None], ci_t, sz[test_idx], sl[test_idx],
                              method=method, c=[fit.c])[:, 0]
            ok_c = np.isfinite(corr)
            if ok_c.sum() > 30:
                a2, _, r2 = _slope_stats(ci_t[ok_c], corr[ok_c])
                mean2 = corr[ok_c].mean()
                if mean2 > 0:
                    eff_a[k] = a2 * (p95 - p05) / mean2
                r_after[k] = r2

    n_ok = int((status == "ok").sum())
    n_deg = int(np.isin(status, ["degenerate", "insufficient"]).sum())
    n_sig_neg = int(np.sum((eff_b < -min_effect) & (t_b < -t_threshold)))
    med_b = float(np.nanmedian(eff_b)) if np.isfinite(eff_b).any() else np.nan
    med_a = float(np.nanmedian(eff_a)) if np.isfinite(eff_a).any() else np.nan
    med_t = float(np.nanmedian(t_b)) if np.isfinite(t_b).any() else np.nan
    if n_deg > nb / 2 or not np.isfinite(med_b):
        verdict = "inconclusive"          # the data could not show a dependence either way
    elif n_sig_neg > nb / 2:
        verdict = "refuse"                # reflectance falls with illumination: over-compensated
    elif abs(med_b) < min_effect or not np.isfinite(med_t) or abs(med_t) < t_threshold:
        verdict = "skip"                  # illumination varies, reflectance (significantly) does not follow
    elif n_ok > nb / 2 and np.isfinite(med_a) and abs(med_a) < abs(med_b) / 2:
        verdict = "correct"               # dependence present and the correction removes most of it
    else:
        verdict = "inconclusive"
    return {"method": method, "n_fit": int(fit_idx.size), "n_test": int(test_idx.size),
            "cos_i_spread": float(np.std(ci[idx])) if idx.size else 0.0,
            "effect_before": eff_b, "effect_after": eff_a, "t_before": t_b,
            "r_before": r_before, "r_after": r_after, "c": c_out, "contrast": contrast,
            "status": status, "median_effect_before": med_b, "median_effect_after": med_a,
            "median_t_before": med_t, "min_effect": min_effect, "verdict": verdict}
