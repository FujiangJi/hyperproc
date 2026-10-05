# hyperproc.correct.brdf.interpolate_coeffs

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def interpolate_coeffs(coeffs, bins, ndvi)
```

Per-pixel ``(f_vol, f_geo, f_iso)`` by linear interpolation in NDVI.

Interpolates each band's coefficients between bin centres, extrapolating
linearly beyond the outer centres. Bins with NaN coefficients are skipped, so a
sparse bin borrows from its neighbours.

Returns:
    ``(n_bands, 3, *ndvi.shape)`` array.

[Module and aliases](../hyperproc-correct-brdf.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.brdf.interpolate_coeffs --runtime`.
