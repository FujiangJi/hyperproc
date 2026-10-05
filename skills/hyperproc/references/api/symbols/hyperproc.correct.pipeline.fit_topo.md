# hyperproc.correct.pipeline.fit_topo

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fit_topo(sample: Sample, method: str='scs+c', fit: str='nnls', calc: dict=TOPO_CALC, apply_spec: dict=TOPO_APPLY, diagnostic_bands: int=40, min_samples: int=100, block_agreement: float=0.7, block_min_pixels: int=500, block_split: int=2, block_t: float=2.0) -> TopoCoefficients
```

Fit one image's topographic coefficients and judge whether to use them.

Every good band gets a :func:`hyperproc.correct.topo.fit_c` - by default
NNLS, which keeps the intercept and therefore C non-negative (an OLS fit
on a product with an additive offset gives C < 0 and a singular factor;
with ``fit="ols"`` such bands come back ``negative_intercept`` and are not
corrected). The illumination diagnostic runs on up to ``diagnostic_bands`` good bands and
its verdict (``correct | skip | refuse | inconclusive``) is stored with the
coefficients. A ``correct`` or ``refuse`` verdict additionally requires
the effect to be spatially consistent - at least ``block_agreement`` of the
sampled blocks, each split into ``block_split x block_split`` sub-blocks
with >= ``block_min_pixels`` fit pixels and a significant slope of their
own (|t| >= ``block_t``), must share the pooled sign and their median
effect must exceed ``min_effect`` - otherwise
it is downgraded to ``inconclusive`` with the reason recorded. Bands the
reader flags bad get status ``bad_band`` and no C.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.fit_topo --runtime`.
