## Satellite MCD43/c-factor/NBAR branch

Use suitable land surface reflectance and actual solar/view geometry. `nbar` does not fit a hyperspectral BRDF from one image. MCD43A1 parameters have coarse approximately 500 m spatial support and a multi-day observation history; mapping them to fine pixels creates no new fine-scale information.

Choose an observed-sun or fixed-sun target deliberately. Default `sza_ref=45.0`, nadir view differs from `sza_ref="observed"`. Record selected target geometry, factors, clipping, snow/quality filters, parameter source/date/footprint and interpolation/filling. `spectral="nearest"` versus `"interp"` trades explicit nearest support versus modeled interpolation; inspect spectral discontinuities near MODIS mapping boundaries.

`params=` accepts prepared parameters. Default external retrieval can use Earth Engine; requires `brdf` dependency, account authorization and `project=`/`EARTHENGINE_PROJECT` as applicable. `source="local"` means existing cache, not automatic missing-data download. `nbar(cache_dir=...)` differs from `mcd43.fetch(out_dir=...)`.

`fill="none"` leaves a neutral factor where parameters are missing and marks it; those pixels are not physically normalized. `median`/`nearest` filling substitutes support and requires disclosure. Inspect `c_factor`, quality/validity flags and footprint coverage. Water/snow/mixed land or extreme angles require separate justification. A common multiplicative scaling of all kernel coefficients cancels in the ratio; arbitrary additive/component biases do not generally cancel, despite broad historical wording.

Lower-level `angles_of`, `lonlat_of`, `band_map`, `band_weights`, `model_reflectance`, `model_agreement`, `view_profile`, `c_factor` support diagnostics and models, not automatic suitability. MCD43 fetch/read/quality helpers have separate dependencies and write/network effects. Read [satellite workflow](https://fujiangji.github.io/hyperproc/workflows/satellite/), [c-factor](../api/hyperproc-correct-cfactor.md), [MCD43](../api/hyperproc-correct-mcd43.md).
