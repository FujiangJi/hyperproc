## Response-resampling details

Review [resampling](../api/hyperproc-spectral-resampling.md) and [SRF](../api/hyperproc-spectral-srf.md). `build_fwhm`, `target_grid`, `resampling_matrix`, and `coverage_of` expose lower-level support checks. Gaussian, box, interpolation and measured-response modes have different assumptions. `min_coverage=0.5` is the default; unsupported output bands are NaN and `band_coverage` records support. Choose stricter support when needed. `allow_sharpening=False` guards unresolved target widths; denser centers do not recover instrument resolution.

SRF registry contains agency Sentinel-2A/B and Landsat 4/5/7/8/9 responses; PlanetScope 4/8 are nominal band-edge approximations. Use `available()` to inspect actual identifiers, then retain URL/source/cache and any approximations. Agency fetching can use network/write cache and may require the `srf` extra. Do not conflate an SRF-capable target sensor with an implemented provider reader or archive collection.

Uncertainty is not completely propagated through these transforms. Inspect returned variables and report dropped or unpropagated uncertainty. Read exact module docs for return structure before composing operations.
