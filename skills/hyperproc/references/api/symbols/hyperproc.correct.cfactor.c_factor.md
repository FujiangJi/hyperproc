# hyperproc.correct.cfactor.c_factor

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def c_factor(params, sza, vza, raa, sza_ref=45.0, vza_ref=0.0, raa_ref=0.0, volume: str='ross_thick', geometric: str='li_sparse_r', b_r: float=1.0, h_b: float=2.0, clip=DEFAULT_CLIP) -> np.ndarray
```

The per-MODIS-band correction ratio, ``(..., 7)``.

Args:
    params: ``(..., 7, 3)`` MCD43A1 weights (NaN where the product has none).
    sza, vza, raa: observed geometry in degrees.
    sza_ref: target solar zenith. A number, ``"observed"`` to keep each
        pixel's own Sun angle, or ``"mean"`` for the scene mean.
    vza_ref, raa_ref: target view geometry, nadir by default.
    clip: ``(lo, hi)`` bounds on the ratio, or None. Ratios outside the
        bounds come from cells where the modelled reflectance at the
        observed geometry is near zero; they are clipped, not dropped.

Returns:
    float32 ``(..., 7)``, NaN where the parameters are missing or the
    model is degenerate.

[Module and aliases](../hyperproc-correct-cfactor.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.cfactor.c_factor --runtime`.
