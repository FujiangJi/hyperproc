# hyperproc.correct.pipeline.view_dependence

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def view_dependence(samples, brdf: BRDFCoefficients | None=None, topo=None, wavelengths=(550, 660, 850, 1650, 2200), ndvi_classes=((0.3, 0.5), (0.5, 0.7), (0.7, 0.9)), calc: dict | None=None) -> dict
```

How much does reflectance still depend on view geometry, per NDVI class?

Within each NDVI class (a proxy for one cover type) the least-squares
slope of reflectance on the volume kernel, times the kernel's p05-p95
span, over the mean reflectance: the view-driven change as a fraction of
the mean. Reported before and, if ``brdf`` is given, after normalisation.
A working correction should cut it several-fold. Pixels come from the
BRDF calc mask - the one the coefficients were fitted with, or ``calc``.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.view_dependence --runtime`.
