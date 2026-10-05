# hyperproc.correct.brdf.apply_flex

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def apply_flex(rho, k_vol, k_geo, ndvi, fit: FlexFit, mask=None, slab=48, ratio_max=5.0)
```

Normalise ``rho (..., band)`` to nadir view at ``fit.sza_ref``.

Pixels where ``mask`` is False, NDVI is outside every bin, or the modelled
observed reflectance is not positive are returned unchanged - the last
because a non-positive denominator means the model does not describe that
pixel and a ratio would be nonsense. The same goes for a ratio outside
``[1/ratio_max, ratio_max]``: a kernel model fitted on a bin describes the
bin's average anisotropy, and a factor of 5 or more only arises where the
modelled reflectance sits at the noise floor (seen at 427-479 nm in a
high-NDVI bin, where -0.0009 became -0.064 without the bound). Such a
pixel/band is left as it is rather than amplified. Bands are processed
``slab`` at a time so the per-pixel interpolated coefficients never
exceed a few hundred MB for a full-swath block.

[Module and aliases](../hyperproc-correct-brdf.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.brdf.apply_flex --runtime`.
