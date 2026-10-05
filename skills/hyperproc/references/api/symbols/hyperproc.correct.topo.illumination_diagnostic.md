# hyperproc.correct.topo.illumination_diagnostic

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def illumination_diagnostic(rho, cos_i, sza, slope, mask, method='scs+c', fit_method='ols', holdout=0.5, seed=0, min_effect=0.01, t_threshold=3.0)
```

How much does reflectance still depend on illumination - and would a
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

[Module and aliases](../hyperproc-correct-topo.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.topo.illumination_diagnostic --runtime`.
