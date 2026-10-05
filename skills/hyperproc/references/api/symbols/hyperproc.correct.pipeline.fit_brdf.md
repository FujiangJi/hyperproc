# hyperproc.correct.pipeline.fit_brdf

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fit_brdf(samples, topo=None, calc: dict=BRDF_CALC, apply_spec: dict=BRDF_APPLY, volume: str='ross_thick', geometric: str='li_dense_r', b_r: float=1.0, h_b: float=2.0, sza_ref='group', num_bins: int=18, ndvi_min: float=0.05, ndvi_max: float=1.0, perc_min: float=10, perc_max: float=95, second_split: bool=True, group_id: str | None=None, force: bool=False, force_topo: bool=False, **diversity_kw) -> BRDFCoefficients
```

Fit FlexBRDF on a group of samples (one site, one flight day) - airborne only.

If ``topo`` (a list of :class:`TopoCoefficients`, one per sample, or
None entries) is given, each sample is topographically corrected first, so
the BRDF fit sees the reflectance it will later be applied to. ``sza_ref``
is ``"group"`` (mean solar zenith of the fitted pixels) or degrees. The
angular-diversity check runs first; an ``insufficient`` verdict raises
unless ``force=True``, because coefficients fitted on a narrow view range
are noise.

A sample is topographically corrected only when its coefficients' verdict
is ``"correct"``; for ``skip``/``refuse``/``inconclusive`` the sample is
used as delivered (with a warning), so the BRDF fit matches what
:func:`apply` will do with the same default. ``force_topo=True`` applies
the coefficients regardless - then pass ``force_topo=True`` to ``apply``
as well, so fit and product agree.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.fit_brdf --runtime`.
