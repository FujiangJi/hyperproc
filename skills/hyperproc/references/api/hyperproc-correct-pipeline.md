# hyperproc.correct.pipeline

Release baseline **0.1.2**; source `hyperproc/correct/pipeline.py`. Choose a callable below rather than loading every declaration.

Run topographic and BRDF corrections on the cubes the readers return.

The flow is *sample -> fit -> apply -> export*, and each step is a function
you can call on its own:

* :func:`sample_image` reads a spread of whole reader chunks from one cube
  (all bands, ~10% of the image, capped) and keeps everything a fit needs:
  reflectance, geometry, NDVI, the six Zhai index bands, the swath footprint.
  Chunk-aligned reads matter: the cubes live on slow disks and a request that
  straddles two compressed chunks costs both.
* :func:`fit_topo` fits one image's SCS+C (or cosine / C / SCS) coefficients
  and runs the illumination diagnostic whose verdict says whether the
  correction is warranted for that product.
* :func:`fit_brdf` pools the samples of a group of images - the lines of one
  site and flight day - and fits FlexBRDF, after checking that the group's
  view geometry is diverse enough for the coefficients to be identifiable.

This module is for **airborne** imaging spectroscopy (NEON AOP, the AVIRIS
family): the corrections rely on per-pixel terrain layers and on the
across-track view-angle diversity of flightline swaths. Satellite products
(EMIT, EnMAP, PRISMA, DESIS, PACE, Tanager) are refused at every entry point.
* :func:`apply` builds the corrected cube lazily (dask), block by block, so
  export streams; :func:`export` writes GeoTIFF + band table + provenance.
* :func:`view_dependence` and :func:`overlap_agreement` are the real-data
  consistency checks the notebooks report.

Nothing here needs a coefficient file from anywhere else; the fits are made
from the cubes themselves and written with :mod:`hyperproc.correct.coefficients`.

## Imported aliases

- `B` → `hyperproc.correct.brdf`
- `M` → `hyperproc.correct.masks`
- `T` → `hyperproc.correct.topo`
- `BRDFCoefficients` → `hyperproc.correct.coefficients.BRDFCoefficients`
- `TopoCoefficients` → `hyperproc.correct.coefficients.TopoCoefficients`
- `align_wavelengths` → `hyperproc.correct.coefficients.align_wavelengths`
- `provenance` → `hyperproc.correct.coefficients.provenance`
- `kernel_pair` → `hyperproc.correct.kernels.kernel_pair`

## Declared callables and classes

- [is_airborne](symbols/hyperproc.correct.pipeline.is_airborne.md)
- [_require_airborne](symbols/hyperproc.correct.pipeline._require_airborne.md) — internal
- [_main_var](symbols/hyperproc.correct.pipeline._main_var.md) — internal
- [_index_bands](symbols/hyperproc.correct.pipeline._index_bands.md) — internal
- [_cloud_stats](symbols/hyperproc.correct.pipeline._cloud_stats.md) — internal
- [_cloud_mask](symbols/hyperproc.correct.pipeline._cloud_mask.md) — internal
- [_geometry_2d](symbols/hyperproc.correct.pipeline._geometry_2d.md) — internal
- [sample_image](symbols/hyperproc.correct.pipeline.sample_image.md)
- [_sample_chunks](symbols/hyperproc.correct.pipeline._sample_chunks.md) — internal
- [_iter_chunks](symbols/hyperproc.correct.pipeline._iter_chunks.md) — internal
- [_sample_pixels](symbols/hyperproc.correct.pipeline._sample_pixels.md) — internal
- [merge_samples](symbols/hyperproc.correct.pipeline.merge_samples.md)
- [per_block_effects](symbols/hyperproc.correct.pipeline.per_block_effects.md)
- [fit_topo](symbols/hyperproc.correct.pipeline.fit_topo.md)
- [angular_diversity](symbols/hyperproc.correct.pipeline.angular_diversity.md)
- [_topo_correct_sample](symbols/hyperproc.correct.pipeline._topo_correct_sample.md) — internal
- [fit_brdf](symbols/hyperproc.correct.pipeline.fit_brdf.md)
- [apply](symbols/hyperproc.correct.pipeline.apply.md)
- [export](symbols/hyperproc.correct.pipeline.export.md)
- [footprint_bounds](symbols/hyperproc.correct.pipeline.footprint_bounds.md)
- [footprint_polygon](symbols/hyperproc.correct.pipeline.footprint_polygon.md)
- [footprint_overlap](symbols/hyperproc.correct.pipeline.footprint_overlap.md)
- [_window_for_bbox](symbols/hyperproc.correct.pipeline._window_for_bbox.md) — internal
- [_window_bounds](symbols/hyperproc.correct.pipeline._window_bounds.md) — internal
- [overlap_windows](symbols/hyperproc.correct.pipeline.overlap_windows.md)
- [find_overlapping_pair](symbols/hyperproc.correct.pipeline.find_overlapping_pair.md)
- [_common_grid](symbols/hyperproc.correct.pipeline._common_grid.md) — internal
- [_reproject](symbols/hyperproc.correct.pipeline._reproject.md) — internal
- [mosaic_geotiffs](symbols/hyperproc.correct.pipeline.mosaic_geotiffs.md)
- [overlap_agreement_tifs](symbols/hyperproc.correct.pipeline.overlap_agreement_tifs.md)
- [seam_check](symbols/hyperproc.correct.pipeline.seam_check.md)
- [view_dependence](symbols/hyperproc.correct.pipeline.view_dependence.md)
- [overlap_agreement](symbols/hyperproc.correct.pipeline.overlap_agreement.md)
- [Sample](symbols/hyperproc.correct.pipeline.Sample.md)

## Constant expressions

- [TOPO_CALC](constants/hyperproc.correct.pipeline.TOPO_CALC.md)
- [TOPO_APPLY](constants/hyperproc.correct.pipeline.TOPO_APPLY.md)
- [BRDF_CALC](constants/hyperproc.correct.pipeline.BRDF_CALC.md)
- [BRDF_APPLY](constants/hyperproc.correct.pipeline.BRDF_APPLY.md)
- [INDEX_BANDS](constants/hyperproc.correct.pipeline.INDEX_BANDS.md)
- [GEOMETRY](constants/hyperproc.correct.pipeline.GEOMETRY.md)
- [AIRBORNE_SENSORS](constants/hyperproc.correct.pipeline.AIRBORNE_SENSORS.md)
