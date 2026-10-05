# Science-readiness acceptance: a result for a stated research task

Surface reflectance is a physical product; “science-ready” additionally depends on the intended analysis. Do not label every output scientifically ready just because it was exported or passed a correction function. Topographic/BRDF/smoothing stages are conditional, not a checklist to apply blindly.

Verify and record:

1. **Physical meaning/calibration:** surface-reflectance interpretation established from provider/retrieval metadata; scale/offset/nodata applied correctly; no TOA reflectance/radiance mislabeled as surface.
2. **Spectral support:** correct nm centers, FWHM/good bands/order and valid index/absorption shoulders. Disclose detector joins, removed bands, synthesized gaps and response simulations.
3. **Observation/QA policy:** valid region, available provider/derived flags, selected exclusions, changed valid fraction and unknown cloud/saturation conditions. Preserve bit meanings and sources.
4. **Ground correspondence:** valid CRS/full affine or justified geolocation/mapping; correct window extent, rotated corners, registration/support where relevant. Same shape is insufficient.
5. **Correction evidence:** atmospheric prerequisites/retrieval diagnostics; topo gate and representative fit; angular support and fitted state for airborne BRDF; MCD43 coverage/quality/targets/filling for satellite normalization. Unwarranted stages stay omitted with reason.
6. **Suitability evaluation:** representative spectra/classes/windows, artifacts/seams/angular residuals and selected independent or held-out comparisons. Provider agreement is informative, not ground truth. Report degradations as well as improvements.
7. **Uncertainty/limitations:** source uncertainty meaning, dropped/unpropagated uncertainty, model/geometry/coarse-parameter assumptions and incomplete validation. Do not invent confidence intervals.
8. **Disk product checks:** reopen with a suitable raster reader; verify count/order, dtype/nodata/NaN patterns, CRS/affine/extent, numeric samples and required sidecars. A nonempty file is not enough.
9. **Reproducibility:** actual package/Python/dependencies, input IDs/fingerprints, grid/window, all effective parameters, masks, coefficients/SRF/priors, cached/reused phases and output locations.

Deliver reflectance plus requested QA/geometry/retrieval/feature products and band metadata/provenance. Keep an original or reconstructible source. Report which criteria were actually checked and whether the result is ready for the stated task, conditionally usable, a preliminary retrieval, or blocked by missing evidence. A provider product can already satisfy many criteria without another atmosphere/BRDF pass.

Read the selected [provider](reflectance-route.md), [atmospheric](atmospheric-route.md), [airborne](airborne-route.md), or [satellite](satellite-route.md) route. More detailed output/uncertainty validation is in [execution and provenance](../operations/execution-validation.md).
