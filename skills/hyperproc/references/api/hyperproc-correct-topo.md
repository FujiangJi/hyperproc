# hyperproc.correct.topo

Release baseline **0.1.2**; source `hyperproc/correct/topo.py`. Choose a callable below rather than loading every declaration.

Topographic (illumination) correction: cosine, C, SCS and SCS+C.

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

## Declared callables and classes

- [cos_incidence](symbols/hyperproc.correct.topo.cos_incidence.md)
- [fit_c](symbols/hyperproc.correct.topo.fit_c.md)
- [fit_c_from_sums](symbols/hyperproc.correct.topo.fit_c_from_sums.md)
- [_check_c](symbols/hyperproc.correct.topo._check_c.md) — internal
- [correction_factor](symbols/hyperproc.correct.topo.correction_factor.md)
- [apply_topo](symbols/hyperproc.correct.topo.apply_topo.md)
- [_slope_stats](symbols/hyperproc.correct.topo._slope_stats.md) — internal
- [illumination_diagnostic](symbols/hyperproc.correct.topo.illumination_diagnostic.md)
- [CFit](symbols/hyperproc.correct.topo.CFit.md)

## Constant expressions

- [METHODS](constants/hyperproc.correct.topo.METHODS.md)
