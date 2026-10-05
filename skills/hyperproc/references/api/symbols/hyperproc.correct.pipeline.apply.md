# hyperproc.correct.pipeline.apply

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def apply(ds: xr.Dataset, topo: TopoCoefficients | None=None, brdf: BRDFCoefficients | None=None, block_bytes: float=200000000.0, notes: dict | None=None, force_topo: bool=False, brdf_ratio_max: float | None=5.0) -> xr.Dataset
```

The corrected cube, lazily: topo first (if given), then BRDF.

The topographic coefficients are applied only when their verdict is
``"correct"``. Otherwise the topo stage is skipped with a warning and the
product is named for the stages actually applied, unless
``force_topo=True`` (recorded in the provenance as ``topo_forced``).
``brdf_ratio_max`` bounds the BRDF factor per pixel and band (see
:func:`hyperproc.correct.brdf.apply_flex`); None disables the bound.

Returns a copy of ``ds`` whose cube is a dask array evaluated block by
block when written; geometry layers and coefficients are aligned to the
cube's wavelength axis here. ``attrs['stem']`` gains ``_topo``, ``_brdf``
or ``_topo_brdf`` so exports never overwrite the input's name.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.apply --runtime`.
