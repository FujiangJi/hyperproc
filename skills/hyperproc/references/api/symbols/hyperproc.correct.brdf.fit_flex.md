# hyperproc.correct.brdf.fit_flex

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fit_flex(rho, k_vol, k_geo, ndvi, bins, min_per_bin=30)
```

Fit f_vol, f_geo, f_iso per band and NDVI bin by least squares.

Args:
    rho: ``(n_samples, n_bands)`` reflectance (any consistent scale).
    k_vol, k_geo: ``(n_samples,)`` kernels at each sample's geometry.
    ndvi: ``(n_samples,)`` used to assign bins.
    bins: from :func:`dynamic_bins` or user-specified ``[[lo, hi], ...]``.
    min_per_bin: bins with fewer samples get NaN coefficients (the apply
        step then falls back to interpolation from neighbours) rather
        than a fit through a handful of points.

Returns:
    ``(coeffs (n_bands, n_bins, 3), n_per_bin, r2)``.

[Module and aliases](../hyperproc-correct-brdf.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.brdf.fit_flex --runtime`.
