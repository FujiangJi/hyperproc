"""EMIT (NASA JPL, aboard the ISS) reader.

EMIT ships each granule as NetCDF-4 with three groups that xarray will not open
together, on a *sensor* grid (downtrack x crosstrack) rather than a map grid.
The ``location`` group carries a GLT (geometry lookup table) that maps it onto
the ortho grid, so orthorectification here is an index lookup, not a resample.

Two products are supported, and they share almost everything:

===========  =====  ==================  ====================
file         level  variable            units
===========  =====  ==================  ====================
``*_RFL_*``  L2A    ``reflectance``     unitless (0-1)
``*_RAD_*``  L1B    ``radiance``        uW/cm^2/SR/nm
===========  =====  ==================  ====================

The ``L2A_MASK`` and ``L1B_OBS`` siblings are picked up automatically for both,
since they describe the same scene. Needs only numpy + xarray.
"""

from __future__ import annotations

import re
from pathlib import Path

import warnings

from hyperproc.readers._common import crs_text, finish_bands, normalise_angles
from hyperproc.readers.aviris import _glt_cube

import numpy as np
import xarray as xr

GLT_NODATA = 0
FILL_VALUE = -9999.0

#: Which products this module can read, and what each one produces.
PRODUCTS = {
    "RFL": {"level": "L2A", "src": "reflectance", "var": "reflectance",
            "units": "1", "long_name": "surface reflectance"},
    "RAD": {"level": "L1B", "src": "radiance", "var": "radiance",
            "units": "uW/cm^2/SR/nm", "long_name": "at-sensor calibrated radiance"},
}

# Band order of the L2A `mask` variable. Bands 5 and 6 are continuous
# retrievals (AOD550, H2O), not flags, so they are read separately.
MASK_FLAGS = {"cloud": 0, "cirrus": 1, "water": 2, "spacecraft": 3, "dilated_cloud": 4}
MASK_VALUES = {"aod550": 5, "h2o_g_cm2": 6}

# Band order of the L1B `obs` variable.
OBS_BANDS = {
    "path_length": 0, "vaa": 1, "vza": 2, "saa": 3, "sza": 4,
    "solar_phase": 5, "slope": 6, "aspect": 7, "cos_i": 8,
    "utc_time": 9, "earth_sun_distance": 10,
}

_GRANULE = re.compile(r"^EMIT_(?P<level>L\d[A-Z])_(?P<product>[A-Z]+)_(?P<rest>.+)\.nc$")


def open_emit(
    path: str | Path,
    ortho: bool = True,
    wl_range: tuple[float, float] | None = None,
    good_bands_only: bool = False,
    masks: bool = True,
    geometry: bool = True,
) -> xr.Dataset:
    """Open an EMIT L2A reflectance or L1B radiance granule.

    Args:
        path: ``EMIT_L2A_RFL_*.nc`` or ``EMIT_L1B_RAD_*.nc``.
        ortho: orthorectify onto the map grid using the granule's GLT.
            False keeps the raw ``(downtrack, crosstrack)`` sensor grid.
        wl_range: ``(min_nm, max_nm)`` band subset, applied *before*
            orthorectification so the full ~5 GB ortho cube is never built.
        good_bands_only: set the bands EMIT flags as unusable to NaN (the
            1320-1440 and 1770-1960 nm water-vapour windows). The band count is
            unchanged - all 285 stay, 41 of them blanked - so band indices keep
            lining up with the sensor's native grid. EMIT stores a constant
            -0.01 sentinel in those bands, which otherwise reads as real data.
            L2A only; L1B granules carry no ``good_wavelengths`` flag.
        masks: fold in the ``L2A_MASK`` sibling if it sits alongside ``path``.
        geometry: fold in the ``L1B_OBS`` sibling if it sits alongside ``path``.

    Returns:
        Dataset with ``reflectance`` or ``radiance`` on ``(y, x, wavelength)``,
        ``wavelength``/``fwhm`` coordinates in nm, plus mask and geometry
        variables where the siblings exist.

    Raises:
        ValueError: not an EMIT granule, or a product this reader does not
            handle (MASK / OBS / RFLUNCERT are read as siblings, not directly).
    """
    path = Path(path)
    m = _GRANULE.match(path.name)
    if m is None:
        raise ValueError(f"{path.name} is not an EMIT granule (expected EMIT_<level>_<product>_*.nc)")

    product = m.group("product")
    if product not in PRODUCTS:
        raise ValueError(
            f"{path.name} is an EMIT {product} product; this reader handles "
            f"{' and '.join(PRODUCTS)}. MASK and OBS are attached automatically "
            f"when you open the RFL or RAD granule."
        )
    spec = PRODUCTS[product]

    root = xr.open_dataset(path)
    bands = xr.open_dataset(path, group="sensor_band_parameters")
    loc = xr.open_dataset(path, group="location")

    wl = bands["wavelengths"].values.astype("float64")
    fwhm = bands["fwhm"].values.astype("float64")
    # Only L2A ships a per-band quality flag.
    good = (bands["good_wavelengths"].values.astype(bool)
            if "good_wavelengths" in bands else None)

    if good_bands_only and good is None:
        raise ValueError(
            f"good_bands_only=True needs the good_wavelengths flag, which "
            f"EMIT ships only on L2A. This is a {spec['level']} {product} granule."
        )

    keep = np.ones(wl.size, dtype=bool)
    if wl_range is not None:
        keep &= (wl >= wl_range[0]) & (wl <= wl_range[1])
    if not keep.any():
        raise ValueError(f"band selection is empty (wl_range={wl_range})")
    bi = np.flatnonzero(keep)

    # Lazy: the cube stays on disk until a block is asked for. The band subset
    # comes first so a wl_range never touches the other bands; the fill -> NaN
    # and good-band blanking are element-wise dask ops.
    src = root[spec["src"]].isel({root[spec["src"]].dims[2]: bi})
    # The file stores the cube contiguously, so xarray would treat it as one
    # 1.8 GB chunk and every window would decode all of it; chunk it first, in
    # the tile shape the GLT gather uses.
    src = src.chunk({src.dims[0]: 256, src.dims[1]: 256, src.dims[2]: 32}).astype("float32")
    src = src.where(src != FILL_VALUE)
    if good_bands_only:
        # Blank the flagged bands rather than dropping them, so the band count
        # and wavelength grid stay aligned with the sensor's native 285. EMIT
        # writes a constant -0.01 sentinel there, not a fill value, so without
        # this they read as plausible data.
        src = src.where(xr.DataArray(good[keep], dims=src.dims[2]))
    src = src.drop_vars(list(src.coords), errors="ignore").rename(
        {src.dims[0]: "y", src.dims[1]: "x", src.dims[2]: "wavelength"})

    glt = _stack_glt(loc) if ortho else None
    if glt is not None:
        # Same lookup-table convention as AVIRIS-5 (1-based, 0 = no data), so
        # the tiled lazy gather written for that reader orthorectifies EMIT too
        # without ever building the ~5 GB ortho cube in memory.
        cube = _glt_cube(src.transpose("wavelength", "y", "x"),
                         glt[..., 0], glt[..., 1]).transpose("y", "x", "wavelength")
    else:
        cube = src

    coords = {
        "wavelength": ("wavelength", wl[keep]),
        "fwhm": ("wavelength", fwhm[keep]),
    }
    if good is not None:
        coords["good_wavelength"] = ("wavelength", good[keep])

    ds = xr.Dataset(
        {spec["var"]: cube},
        coords=coords,
        attrs={
            "sensor": "EMIT",
            "level": spec["level"],
            "product": product,
            "granule": path.stem,
            "datetime": root.attrs.get("time_coverage_start", ""),
            "units": spec["units"],
            "orthorectified": int(ortho),
        },
    )
    ds["wavelength"].attrs.update(units="nm", long_name="band centre")
    ds["fwhm"].attrs.update(units="nm", long_name="band width")
    ds[spec["var"]].attrs.update(units=spec["units"], long_name=spec["long_name"])

    if ortho:
        gt = np.asarray(root.attrs["geotransform"], dtype="float64").ravel()
        ds.attrs["crs"] = crs_text(root.attrs.get("spatial_ref")) or "EPSG:4326"
        ds.attrs["transform"] = tuple(float(v) for v in gt)
        ds = ds.assign_coords(
            x=("x", gt[0] + (np.arange(ds.sizes["x"]) + 0.5) * gt[1]),
            y=("y", gt[3] + (np.arange(ds.sizes["y"]) + 0.5) * gt[5]),
        )
        ds["x"].attrs.update(units="degrees_east", standard_name="longitude")
        ds["y"].attrs.update(units="degrees_north", standard_name="latitude")
        ds["elev"] = (("y", "x"), _apply_glt(loc["elev"].values.astype("float32"), glt)[..., 0])
    else:
        ds["elev"] = (("y", "x"), loc["elev"].values.astype("float32"))
        # The sensor grid has no CRS; its geolocation arrays are what
        # hyperproc.georeference needs.
        for name in ("lat", "lon"):
            ds[name] = (("y", "x"), loc[name].values.astype("float64"))
        ds["lat"].attrs.update(units="degrees_north", long_name="latitude")
        ds["lon"].attrs.update(units="degrees_east", long_name="longitude")
    ds["elev"].attrs.update(units="m", long_name="surface elevation")

    rest = m.group("rest")
    if masks:
        _add_masks(ds, path, rest, glt)
    if geometry:
        _add_geometry(ds, path, rest, glt)
    good_src = "provider flag (good_wavelengths)"
    if good is None:
        # L1B ships no flag, but the L2A reflectance of the same scene does.
        sib = _sibling(path, "L2A", "RFL", rest)
        if sib is not None:
            try:
                good = xr.open_dataset(sib, group="sensor_band_parameters")["good_wavelengths"].values.astype(bool)
                good_src = f"good_wavelengths of the L2A sibling {sib.name}"
            except (OSError, KeyError):
                good = None
    finish_bands(ds, index=bi, good=None if good is None else good[keep], good_source=good_src,
                 fill_value=FILL_VALUE)
    normalise_angles(ds)
    return ds


def _sibling(path: Path, level: str, product: str, rest: str) -> Path | None:
    """The sibling granule, tolerating a different processing-version suffix.

    ``rest`` ends in the version (``..._2311213_002``); a MASK or OBS
    reprocessed to ``_003`` next to an RFL at ``_002`` is still the same scene,
    so fall back to the newest version of the same scene id.
    """
    cand = path.with_name(f"EMIT_{level}_{product}_{rest}.nc")
    if cand.exists():
        return cand
    scene = rest.rsplit("_", 1)[0]
    hits = sorted(path.parent.glob(f"EMIT_{level}_{product}_{scene}_*.nc"))
    return hits[-1] if hits else None


def _add_masks(ds: xr.Dataset, path: Path, rest: str, glt) -> None:
    src = _sibling(path, "L2A", "MASK", rest)
    if src is None:
        ds.attrs["mask_source"] = "none"
        warnings.warn(f"{path.name}: no MASK sibling (expected EMIT_L2A_MASK_{rest}.nc next to it); "
                      "cloud/cirrus/water flags not attached")
        return
    arr = xr.open_dataset(src)["mask"].values.astype("float32")
    if glt is not None:
        arr = _apply_glt(arr, glt)
    for name, i in MASK_FLAGS.items():
        ds[name] = (("y", "x"), np.nan_to_num(arr[..., i], nan=0.0) > 0)
        ds[name].attrs["long_name"] = f"{name.replace('_', ' ')} flag"
    for name, i in MASK_VALUES.items():
        ds[name] = (("y", "x"), arr[..., i])
    ds.attrs["mask_source"] = src.name


def _add_geometry(ds: xr.Dataset, path: Path, rest: str, glt) -> None:
    src = _sibling(path, "L1B", "OBS", rest)
    if src is None:
        ds.attrs["obs_source"] = "none"
        warnings.warn(f"{path.name}: no OBS sibling (expected EMIT_L1B_OBS_{rest}.nc next to it); "
                      "geometry layers (sza, saa, vza, vaa, slope, aspect) not attached")
        return
    arr = xr.open_dataset(src)["obs"].values.astype("float32")
    arr[arr == FILL_VALUE] = np.nan
    if glt is not None:
        arr = _apply_glt(arr, glt)
    for name, i in OBS_BANDS.items():
        ds[name] = (("y", "x"), arr[..., i])
    for name in ("sza", "vza", "saa", "vaa", "slope", "aspect", "solar_phase"):
        ds[name].attrs["units"] = "degrees"
    # Relative azimuth as every other reader reports it; the BRDF kernels take
    # this angle and export_geometry lists it.
    ds["raa"] = (("y", "x"), np.mod(ds["vaa"].values - ds["saa"].values, 360.0).astype("float32"))
    ds["raa"].attrs.update(units="degrees", long_name="relative azimuth (VAA - SAA, mod 360)")
    ds.attrs["obs_source"] = src.name


def _stack_glt(loc: xr.Dataset) -> np.ndarray:
    """(y, x, 2) of 1-based (crosstrack, downtrack) lookups; 0 means no data."""
    return np.nan_to_num(
        np.stack([loc["glt_x"].data, loc["glt_y"].data], axis=-1), nan=GLT_NODATA
    ).astype(int)


def _apply_glt(arr: np.ndarray, glt: np.ndarray) -> np.ndarray:
    """Map a sensor-grid array onto the ortho grid. Always returns 3-D."""
    if arr.ndim == 2:
        arr = arr[:, :, np.newaxis]
    out = np.full((glt.shape[0], glt.shape[1], arr.shape[-1]), np.nan, dtype="float32")
    valid = np.all(glt != GLT_NODATA, axis=-1)
    idx = glt.copy()
    idx[valid] -= 1  # GLT is 1-based
    out[valid, :] = arr[idx[valid, 1], idx[valid, 0], :]
    return out
