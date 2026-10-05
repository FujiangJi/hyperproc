# hyperproc.correct

Release baseline **0.1.2**; source `hyperproc/correct/__init__.py`. Choose a callable below rather than loading every declaration.

Topographic and BRDF correction for the cubes the readers return.

The math lives in small, separately testable modules:

* :mod:`hyperproc.correct.kernels` - Ross and Li BRDF kernels.
* :mod:`hyperproc.correct.topo` - cosine, C, SCS and SCS+C corrections and the
  illumination-dependence diagnostic that decides whether to apply one.
* :mod:`hyperproc.correct.brdf` - FlexBRDF: per-NDVI-bin kernel fits pooled
  across a group of images, applied as a nadir normalisation.
* :mod:`hyperproc.correct.mcd43` - MODIS MCD43A1 BRDF model parameters, fetched
  for a scene's footprint and date.
* :mod:`hyperproc.correct.cfactor` - the c-factor normalisation for satellite
  scenes, which borrow their BRDF shape from MODIS because one overpass cannot
  measure it.
* :mod:`hyperproc.correct.masks` - the pixel masks the fits are drawn from.
* :mod:`hyperproc.correct.coefficients` - wavelength-keyed coefficient files
  with fit diagnostics and provenance.
* :mod:`hyperproc.correct.pipeline` - sample -> fit -> apply -> export on real
  airborne cubes (NEON, AVIRIS), with the gates that decide whether a
  correction is warranted. A satellite scene has no angular spread to fit, so
  it goes through :mod:`~hyperproc.correct.cfactor` instead.

Everything here is written from the primary literature and checked against
synthetic data with known answers (``tests/test_correct_*.py``) and against
an independent implementation on real NEON flightlines.

## Declared exports

`brdf`, `cfactor`, `coefficients`, `masks`, `mcd43`, `pipeline`, `topo`, `angles_of`, `band_map`, `band_weights`, `c_factor`, `lonlat_of`, `model_agreement`, `model_reflectance`, `nbar`, `view_profile`, `BRDFCoefficients`, `TopoCoefficients`, `load`, `angular_diversity`, `apply`, `export`, `find_overlapping_pair`, `fit_brdf`, `fit_topo`, `footprint_bounds`, `footprint_overlap`, `footprint_polygon`, `is_airborne`, `merge_samples`, `mosaic_geotiffs`, `overlap_agreement`, `overlap_agreement_tifs`, `overlap_windows`, `per_block_effects`, `sample_image`, `seam_check`, `view_dependence`, `GEOMETRIC_KERNELS`, `VOLUME_KERNELS`, `geometric_kernel`, `kernel_pair`, `phase_angle`, `reference_kernels`, `volume_kernel`

## Imported aliases

- `brdf` → `hyperproc.correct.brdf`
- `cfactor` → `hyperproc.correct.cfactor`
- `coefficients` → `hyperproc.correct.coefficients`
- `masks` → `hyperproc.correct.masks`
- `mcd43` → `hyperproc.correct.mcd43`
- `pipeline` → `hyperproc.correct.pipeline`
- `topo` → `hyperproc.correct.topo`
- `BRDFCoefficients` → `hyperproc.correct.coefficients.BRDFCoefficients`
- `TopoCoefficients` → `hyperproc.correct.coefficients.TopoCoefficients`
- `load` → `hyperproc.correct.coefficients.load`
- `angular_diversity` → `hyperproc.correct.pipeline.angular_diversity`
- `apply` → `hyperproc.correct.pipeline.apply`
- `export` → `hyperproc.correct.pipeline.export`
- `find_overlapping_pair` → `hyperproc.correct.pipeline.find_overlapping_pair`
- `fit_brdf` → `hyperproc.correct.pipeline.fit_brdf`
- `fit_topo` → `hyperproc.correct.pipeline.fit_topo`
- `footprint_bounds` → `hyperproc.correct.pipeline.footprint_bounds`
- `footprint_overlap` → `hyperproc.correct.pipeline.footprint_overlap`
- `footprint_polygon` → `hyperproc.correct.pipeline.footprint_polygon`
- `is_airborne` → `hyperproc.correct.pipeline.is_airborne`
- `merge_samples` → `hyperproc.correct.pipeline.merge_samples`
- `mosaic_geotiffs` → `hyperproc.correct.pipeline.mosaic_geotiffs`
- `overlap_agreement` → `hyperproc.correct.pipeline.overlap_agreement`
- `overlap_agreement_tifs` → `hyperproc.correct.pipeline.overlap_agreement_tifs`
- `overlap_windows` → `hyperproc.correct.pipeline.overlap_windows`
- `per_block_effects` → `hyperproc.correct.pipeline.per_block_effects`
- `sample_image` → `hyperproc.correct.pipeline.sample_image`
- `seam_check` → `hyperproc.correct.pipeline.seam_check`
- `view_dependence` → `hyperproc.correct.pipeline.view_dependence`
- `angles_of` → `hyperproc.correct.cfactor.angles_of`
- `band_map` → `hyperproc.correct.cfactor.band_map`
- `band_weights` → `hyperproc.correct.cfactor.band_weights`
- `c_factor` → `hyperproc.correct.cfactor.c_factor`
- `lonlat_of` → `hyperproc.correct.cfactor.lonlat_of`
- `model_agreement` → `hyperproc.correct.cfactor.model_agreement`
- `model_reflectance` → `hyperproc.correct.cfactor.model_reflectance`
- `nbar` → `hyperproc.correct.cfactor.nbar`
- `view_profile` → `hyperproc.correct.cfactor.view_profile`
- `GEOMETRIC_KERNELS` → `hyperproc.correct.kernels.GEOMETRIC_KERNELS`
- `VOLUME_KERNELS` → `hyperproc.correct.kernels.VOLUME_KERNELS`
- `geometric_kernel` → `hyperproc.correct.kernels.geometric_kernel`
- `kernel_pair` → `hyperproc.correct.kernels.kernel_pair`
- `phase_angle` → `hyperproc.correct.kernels.phase_angle`
- `reference_kernels` → `hyperproc.correct.kernels.reference_kernels`
- `volume_kernel` → `hyperproc.correct.kernels.volume_kernel`

## Declared callables and classes

