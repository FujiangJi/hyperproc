"""Topographic and BRDF correction for the cubes the readers return.

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
"""

from hyperproc.correct import brdf, cfactor, coefficients, masks, mcd43, pipeline, topo  # noqa: F401  submodules
from hyperproc.correct.coefficients import BRDFCoefficients, TopoCoefficients, load
from hyperproc.correct.pipeline import (angular_diversity, apply, export, find_overlapping_pair, fit_brdf, fit_topo,
                                        footprint_bounds, footprint_overlap, footprint_polygon, is_airborne, merge_samples, mosaic_geotiffs, overlap_agreement,
                                        overlap_agreement_tifs, overlap_windows, per_block_effects,
                                        sample_image, seam_check, view_dependence)
from hyperproc.correct.cfactor import (angles_of, band_map, band_weights, c_factor, lonlat_of,
                                       model_agreement, model_reflectance, nbar, view_profile)
from hyperproc.correct.kernels import (
    GEOMETRIC_KERNELS, VOLUME_KERNELS, geometric_kernel, kernel_pair, phase_angle,
    reference_kernels, volume_kernel,
)

__all__ = [
    "brdf", "cfactor", "coefficients", "masks", "mcd43", "pipeline", "topo",
    "angles_of", "band_map", "band_weights", "c_factor", "lonlat_of", "model_agreement",
    "model_reflectance",
    "nbar", "view_profile",
    "BRDFCoefficients", "TopoCoefficients", "load",
    "angular_diversity", "apply", "export", "find_overlapping_pair", "fit_brdf", "fit_topo", "footprint_bounds", "footprint_overlap", "footprint_polygon",
    "is_airborne", "merge_samples", "mosaic_geotiffs", "overlap_agreement", "overlap_agreement_tifs", "overlap_windows",
    "per_block_effects", "sample_image", "seam_check", "view_dependence",
    "GEOMETRIC_KERNELS", "VOLUME_KERNELS", "geometric_kernel", "kernel_pair",
    "phase_angle", "reference_kernels", "volume_kernel",
]
