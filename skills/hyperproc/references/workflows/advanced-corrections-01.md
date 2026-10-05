## Atmospheric branch

### Preconditions and physical inputs

Use calibrated supported at-sensor inputs with the necessary acquisition metadata, wavelength/FWHM support, elevation, solar/view geometry, and geolocation. Standardized radiance for prepared ISOFIT inputs is µW cm⁻² nm⁻¹ sr⁻¹. Actual readers use sensor-specific units: e.g. EnMAP L1 W m⁻² sr⁻¹ nm⁻¹, DESIS mW cm⁻² sr⁻¹ µm⁻¹, Tanager W m⁻² sr⁻¹ µm⁻¹. Use the package preparation conversion; never multiply all products by a guessed common factor. PACE's TOA-reflectance route has its own conversion; NEON reflectance and PRISMA L2B surface radiance are not L1 radiance.

The preparation pathway limits radiative-transfer inputs to 350–2500 nm. Preserve its band table and excluded-band decisions. Missing geometry/elevation requires a supported source or explicitly justified approximation; do not substitute invented arrays. DEM helpers can fetch/cache external elevation; review region coverage and any fallback. Surface priors are model assumptions, not proof of true reflectance.

### High-level versus staged API

- `hyperproc.atmos.check`: asset/engine diagnostic; `setup`: provisioning/configuration effects.
- `process`: orchestrates supported stages, input preparation, retrieval, mapping and exports. Choose `stages=("ac",)` initially; optional satellite BRDF is separate from grouped airborne FlexBRDF.
- `prepare_inputs`: writes ISOFIT radiance/location/observation ENVI inputs and spectral metadata.
- `build_command`: resolves engine and retrieval controls; inspect emitted arguments/settings.
- `correct`: executes/resumes retrieval; `read_outputs`: reopens available retrieval results.
- `to_map_grid`: relevant existing map grid, EMIT GLT, or available geolocation mapping.
- Engine/DEM/aerosol helpers: inspect exact modules before calling them directly; internal `_runner` helpers are implementation details.

Read [atmosphere workflow](https://fujiangji.github.io/hyperproc/workflows/atmosphere/), [process](../api/hyperproc-atmos-process.md), [correction](../api/hyperproc-atmos-correct.md), [input preparation](../api/hyperproc-atmos-inputs.md), [DEM](../api/hyperproc-atmos-dem.md), [engines](../api/hyperproc-atmos-engines.md), [aerosols](../api/hyperproc-atmos-aerosols.md), and [setup](../api/hyperproc-atmos-setup.md) as needed.

### Controlled experiment

Check assets before retrieval. Choose a representative valid bounded region, unique work/output directory, explicitly budgeted workers/disk and engine. Record surface model/prior, segmentation, atmosphere prior/uncertainty, interpolation controls, config overrides, and reused intermediate products. sRTMnet, 6S and LibRadTran are distinct supported configurations with different assets/engine assumptions. Do not silently fall back between engines or priors after a failure.

`resolve_neighbors` caps interpolation neighbor counts using valid fraction × rows × columns divided by segmentation size, with a conservative half-count and minimum five. Previous measured segment counts may lower the cap to 80% of measured labels, never raise it. Scalar/per-term neighbor settings are resolved by the released implementation. A smaller window does not justify arbitrary large neighbor requests; minimum five is an implementation bound, not evidence five segments exist or fitting is valid.

`dry_run` can write prepared inputs. Reused outputs must match exact scene/window/settings. `redo="line"` is not full fresh inversion. On failure keep relevant nonsecret logs, phase reached and work-product inventory; diagnose missing assets, radiometry, segmentation or interpolation instead of repeatedly launching the same expensive operation.

### Output evaluation

Inspect reflectance, available aot550/h2o/retrieval layers, ac_failed/fill and geographic consistency. Compare multiple surfaces and wavelengths to provider products or independent references. Provider agreement is not ground truth, especially when priors/input products are related. Report fresh retrieval time separately from cached processing, export and interpolation.
