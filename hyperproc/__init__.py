"""hyperproc - one interface for airborne and spaceborne imaging spectroscopy.

    import hyperproc as hp

    ds = hp.open(path, sensor="EMIT", level="L2A")   # explicit
    ds = hp.open(path)                                # guessed from the filename
    hp.describe(ds)
    hp.list_readers()

Every reader returns an ``xarray.Dataset`` with the same shape of metadata:
``reflectance(y, x, wavelength)``, ``wavelength`` and ``fwhm`` coordinates in
nm, plus mask and geometry variables where the sensor provides them.
"""

from __future__ import annotations

import os as _os

# GDAL's raster block cache defaults to 5 % of RAM (10 GB on a 188 GB server).
# Streaming a cube reads every block once, so a large cache only inflates the
# process: loading one AVIRIS line's six geometry layers left 2.5 GB resident
# with the default and 0.7 GB with a small cache. Bound it unless the user has
# set GDAL_CACHEMAX (megabytes) themselves. Must precede the first rasterio import.
_os.environ.setdefault("GDAL_CACHEMAX", "1024")

import builtins
from pathlib import Path

import xarray as xr

from hyperproc.registry import REGISTRY, Entry, list_readers, resolve, sniff, summary
from hyperproc.align import apply_shift, coregister, estimate_shift, tie_points
from hyperproc.grid import georeference, latlon_grid, utm_epsg
from hyperproc.io import (FORMATS, GEOMETRY_LAYERS, bands_to_csv, build_overviews,
                          default_name, envi_header, export_geometry, main_var, to_envi,
                          to_geotiff, to_geotiff_2d, to_latlon_geotiff, to_raster)
from hyperproc.readers.aviris import check_geometry, fix_slope_convention
from hyperproc import align, archive, features, quality, spectral
from hyperproc.archive import download, files, search
from hyperproc.features import band_depth, describe_indices
from hyperproc.features import index as spectral_index
from hyperproc.spectral import (band_at, continuum_removal, find_spikes, resample,
                                smooth_spectra, spline_gapfill)
from hyperproc.spectral import derivative as spectral_derivative
from hyperproc.quality import apply as quality_apply
from hyperproc.quality import build as quality_flags
from hyperproc.quality import decode as quality_decode
from hyperproc.quality import describe as quality_table
from hyperproc.quality import summary as quality_summary
from hyperproc.report import describe

__version__ = "0.1.1"

__all__ = [
    "open", "read", "describe", "list_readers", "sniff", "summary",
    "to_geotiff", "to_geotiff_2d", "to_envi", "to_raster", "envi_header", "FORMATS",
    "build_overviews", "bands_to_csv", "main_var", "default_name",
    "export_geometry", "GEOMETRY_LAYERS", "check_geometry", "fix_slope_convention",
    "georeference", "utm_epsg", "latlon_grid", "to_latlon_geotiff", "smooth_spectra",
    "align", "coregister", "estimate_shift", "apply_shift", "tie_points",
    "quality", "quality_flags", "quality_apply", "quality_decode", "quality_summary", "quality_table",
    "features", "spectral", "band_at", "band_depth", "continuum_removal", "describe_indices", "resample", "find_spikes", "spline_gapfill",
    "spectral_derivative", "spectral_index",
    "REGISTRY", "Entry", "__version__",
    # finding data, before reading it
    "archive", "search", "download", "files", "search_map",
]


def open(  # noqa: A001 - mirrors xarray.open_dataset; builtins.open still available
    path: str | Path,
    sensor: str | None = None,
    level: str | None = None,
    **kwargs,
) -> xr.Dataset:
    """Open a hyperspectral granule with the right reader for its sensor.

    Args:
        path: the granule to read. For sensors that split a scene across
            several files (EMIT, PACE), pass the main reflectance/radiance
            file; siblings are located automatically.
        sensor: ``"EMIT"``, ``"PRISMA"``, ``"ENMAP"``, ``"DESIS"``, ``"PACE"``,
            ``"AVIRIS"``, ``"NEON"``. Guessed from the filename if omitted.
        level: ``"L1B"``, ``"L2A"``, ``"L2D"``, ... Guessed if omitted.
        **kwargs: passed through to the sensor's reader. EMIT accepts
            ``ortho``, ``wl_range``, ``good_bands_only``, ``masks``, ``geometry``.

    Returns:
        ``xarray.Dataset``. See :func:`describe` for a quick look.

    Raises:
        ValueError: the sensor/level is unknown, or the filename could not be
            identified and nothing was passed explicitly.
        NotImplementedError: the sensor/level is registered but its reader is
            not written yet. The message says what to write.

    Examples:
        >>> ds = hyperproc.open("EMIT_L2A_RFL_001_20230422T195924_2311213_002.nc")
        >>> ds = hyperproc.open(p, sensor="EMIT", level="L2A", wl_range=(400, 900))
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    entry = resolve(path, sensor, level)
    if path.is_dir() and entry.sensor != "AVIRIS":
        raise ValueError(f"{path} is a directory; {entry.sensor} readers take the granule file "
                         f"itself (expected {entry.expects})")
    ds = entry.loader(path, **kwargs)
    # Remember where the data came from: the atmospheric-correction step
    # needs the granule again (EMIT's GLT lives in the L1B file).
    ds.attrs.setdefault("source", str(path.resolve()))
    return ds


#: Alias, for when ``open`` shadowing the builtin reads badly at a call site.
read = open


def open_builtin(*args, **kwargs):
    """Escape hatch: the real :func:`builtins.open`, in case this module's is imported."""
    return builtins.open(*args, **kwargs)


def __getattr__(name):
    # the interactive search map needs ipyleaflet; importing hyperproc must not
    if name == "search_map":
        from hyperproc.archive import search_map
        return search_map
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
