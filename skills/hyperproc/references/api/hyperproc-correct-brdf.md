# hyperproc.correct.brdf

Release baseline **0.1.2**; source `hyperproc/correct/brdf.py`. Choose a callable below rather than loading every declaration.

FlexBRDF: kernel-driven BRDF normalisation, stratified by NDVI.

From Queally et al. (2022), *FlexBRDF: A flexible BRDF correction for grouped
processing of airborne imaging spectroscopy flightlines*, JGR Biogeosciences,
The model per band and per NDVI class is the
Ross-Li linear kernel model of Lucht et al. (2000):

    rho(sza, vza, raa) = f_iso + f_vol K_vol(sza, vza, raa) + f_geo K_geo(sza, vza, raa)

and the correction is a multiplicative normalisation of each pixel to a
reference geometry - nadir view under a chosen solar zenith:

    rho_ref = rho * (f_iso + f_vol K_vol_ref + f_geo K_geo_ref)
                  / (f_iso + f_vol K_vol     + f_geo K_geo)

Three things make it "flex":

1. **NDVI stratification.** Coefficients are fitted separately for NDVI bins,
   because the anisotropy of bare soil, sparse and dense canopies differs.
   Bin edges are *dynamic* - percentiles of the pooled NDVI between
   ``perc_min`` and ``perc_max`` - so each bin holds a comparable number of
   pixels (:func:`dynamic_bins`).
2. **Grouped fitting.** The samples are pooled across every flightline in a
   group before fitting, so one coefficient set applies to all of them and
   seams between adjacent lines close. Grouping is the caller's job (the
   pipeline pools ``samples`` from many images); this module fits what it is
   given.
3. **Interpolation across bins.** At apply time the per-bin coefficients are
   interpolated linearly in NDVI (with extrapolation at the ends), so the
   correction is continuous rather than stepped at bin boundaries.

Scale invariance, worth knowing: the correction is a ratio of the same linear
model, so coefficients fitted on reflectance x 10 000 (as EnSpec's NEON
coefficient files were) apply unchanged to reflectance in 0-1.

## Imported aliases

- `kernel_pair` → `hyperproc.correct.kernels.kernel_pair`
- `reference_kernels` → `hyperproc.correct.kernels.reference_kernels`

## Declared callables and classes

- [dynamic_bins](symbols/hyperproc.correct.brdf.dynamic_bins.md)
- [_second_split](symbols/hyperproc.correct.brdf._second_split.md) — internal
- [assign_bins](symbols/hyperproc.correct.brdf.assign_bins.md)
- [bin_centres](symbols/hyperproc.correct.brdf.bin_centres.md)
- [fit_flex](symbols/hyperproc.correct.brdf.fit_flex.md)
- [interpolate_coeffs](symbols/hyperproc.correct.brdf.interpolate_coeffs.md)
- [apply_flex](symbols/hyperproc.correct.brdf.apply_flex.md)
- [fit_group](symbols/hyperproc.correct.brdf.fit_group.md)
- [FlexFit](symbols/hyperproc.correct.brdf.FlexFit.md)
