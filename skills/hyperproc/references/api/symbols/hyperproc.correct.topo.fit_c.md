# hyperproc.correct.topo.fit_c

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fit_c(rho, cos_i, method='ols', min_samples=100, min_spread=0.02, neg_tol=0.05)
```

Fit C = intercept / slope of ``rho = a cos_i + b`` (Teillet 1982; Soenen 2005 eq 7-8).

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

[Module and aliases](../hyperproc-correct-topo.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.topo.fit_c --runtime`.
