"""Per-spectrum transforms: a cube goes in, a cube comes out.

    hyperproc.spectral.bands        addressing a band by wavelength
    hyperproc.spectral.smoothing    Savitzky-Golay and moving-average smoothing
    hyperproc.spectral.continuum    continuum removal by convex hull
    hyperproc.spectral.derivatives  first and second derivatives
    hyperproc.spectral.resampling   putting a cube on another band set
    hyperproc.spectral.srf          published response functions, fetched and cached

Operations that reduce a spectrum to one number per pixel - spectral indices
and absorption depths - live in :mod:`hyperproc.features` instead, because
what comes out of them is a map, not a cube.
"""
from hyperproc.spectral import bands, continuum, derivatives, resampling, smoothing, srf  # noqa: F401
from hyperproc.spectral.bands import TOLERANCE, band_at, good_bands, runs_of_good_bands
from hyperproc.spectral.continuum import continuum_removal
from hyperproc.spectral.derivatives import derivative
from hyperproc.spectral.resampling import METHODS, build_fwhm, resample, resampling_matrix, target_grid
from hyperproc.spectral.smoothing import (PRISMA_ARTEFACT_RANGES, PRISMA_MASK_AFTER,
                                           find_spikes, smooth_spectra, spline_gapfill)

__all__ = ["bands", "continuum", "derivatives", "resampling", "smoothing", "srf",
           "TOLERANCE", "band_at", "good_bands", "runs_of_good_bands",
           "continuum_removal", "derivative", "smooth_spectra", "find_spikes", "spline_gapfill",
           "PRISMA_ARTEFACT_RANGES", "PRISMA_MASK_AFTER",
           "METHODS", "build_fwhm", "resample", "resampling_matrix", "target_grid"]
