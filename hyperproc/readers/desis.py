"""DESIS (DLR Earth Sensing Imaging Spectrometer) reader for L1B / L1C / L2A.

DESIS flew on the ISS MUSES platform from 2018 until the mission ended on
2023-12-31, so these are archive products. It is a **VNIR-only** instrument:
235 bands from 401 to 1000 nm, 30 m, with no SWIR at all.

Each product is a plain GeoTIFF of ``int16`` DN plus an XML sidecar, so unlike
EMIT or PRISMA nothing is self-describing - the wavelengths, the per-band
scaling and every viewing angle live in ``*-METADATA.xml``:

    value = DN * gainOfBand + offsetOfBand

L2A uses a single gain of 1e-4 with zero offset. **L1B and L1C carry a
different gain *and* a different offset for every one of the 235 bands**, so
applying a scene-wide scale factor - the obvious shortcut - is wrong there.

============  =========================  =============  ==================
level         grid                       variable       georeferencing
============  =========================  =============  ==================
L1B           1024 x 1024 sensor grid    radiance       none
L1C           1493 x 1493 UTM, 30 m      radiance       EPSG + transform
L2A           1493 x 1493 UTM, 30 m      reflectance    EPSG + transform
============  =========================  =============  ==================

Angles are **scene-level scalars**, not per-pixel rasters, and land in
``ds.attrs``: DESIS ships no equivalent of EMIT's OBS file.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from hyperproc.readers._common import crs_text, finish_bands, normalise_angles
import xarray as xr

NODATA = -32768

#: Product level -> (variable name, units, long name).
LEVEL_SPEC = {
    # DLR ATBD PAV-DLR-TN-004: TOA radiance in mW/(cm^2 sr um), which is the
    # same unit EMIT reports as uW/cm^2/SR/nm. Verified against a radiative
    # estimate for this scene: 2.45 -> 24.5 mW/m^2/sr/nm at 550 nm, inside the
    # 13-23 expected from the L2A reflectance, solar geometry and path radiance.
    "L1B": ("radiance", "mW/cm^2/sr/um", "at-sensor TOA radiance"),
    "L1C": ("radiance", "mW/cm^2/sr/um", "at-sensor TOA radiance, orthorectified"),
    "L2A": ("reflectance", "1", "surface reflectance"),
}

#: Band order of the L2A ``QL_QUALITY-2`` file, from its own descriptions.
QUALITY_FLAGS = {
    "shadow": 0, "land": 1, "snow": 2, "haze_land": 3, "haze_water": 4,
    "cloud_land": 5, "cloud_water": 6, "water": 7,
}
#: The last two bands are scaled retrievals rather than flags.
QUALITY_VALUES = {"aot550": (8, 0.01), "wv_cm": (9, 1.0 / 42.0)}

#: Scene-level metadata worth keeping, XML tag -> attribute name.
SCENE_TAGS = {
    "sunZenithAngle": "sun_zenith", "sunAzimuthAngle": "sun_azimuth",
    "sceneIncidenceAngle": "view_zenith",
    # sceneAzimuthAngle is NOT a view azimuth: the same acquisition reports
    # 36.3 on L1B and 307.9 on L1C/L2A. Kept under its own name only.
    "sceneAzimuthAngle": "scene_azimuth_angle", "startTime": "datetime",
    "pointingMirrorAngle": "pointing_mirror_angle",
    "percentageClouds": "cloudy_pixels_pct",
    "percentageCloudShadow": "cloud_shadow_pct",
}

_GRANULE = re.compile(r"^DESIS-HSI-(?P<level>L1B|L1C|L2A)-(?P<rest>.+)-SPECTRAL_IMAGE\.tif$",
                      re.IGNORECASE)


def open_desis(
    path: str | Path,
    wl_range: tuple[float, float] | None = None,
    quality: bool = True,
    band_quality: bool = False,
    apply_scale: bool = True,
) -> xr.Dataset:
    """Open a DESIS granule.

    Args:
        path: the ``*-SPECTRAL_IMAGE.tif``. The ``METADATA.xml`` and quality
            siblings are found beside it by name.
        wl_range: ``(min_nm, max_nm)`` band subset. DESIS covers 401-1000 nm.
        quality: attach the L2A ``QL_QUALITY-2`` layers - ``shadow``, ``land``,
            ``snow``, ``haze_land``, ``haze_water``, ``cloud_land``,
            ``cloud_water``, ``water``, plus ``aot550`` and ``wv_cm``. A
            combined ``cloud`` is derived from the two cloud flags.
        band_quality: attach the 235-band per-band quality raster as
            ``band_quality``. Adds a uint8 array the size of the cube.
        apply_scale: convert DN to physical units with the per-band gain and
            offset. ``False`` returns raw ``int16`` DN, for debugging.

    Returns:
        Dataset with ``radiance`` or ``reflectance`` on ``(y, x, wavelength)``
        and ``wavelength``/``fwhm`` coordinates in nm.
    """
    import rasterio

    path = Path(path)
    m = _GRANULE.match(path.name)
    if m is None:
        raise ValueError(
            f"{path.name} is not a DESIS spectral image "
            f"(expected DESIS-HSI-<L1B|L1C|L2A>-*-SPECTRAL_IMAGE.tif)"
        )
    level = m.group("level").upper()
    var, units, long_name = LEVEL_SPEC[level]

    meta_path = _sibling(path, "METADATA.xml")
    if meta_path is None:
        raise FileNotFoundError(
            f"{path.name} needs its METADATA.xml sibling - DESIS GeoTIFFs carry "
            f"no wavelengths or scaling of their own."
        )
    wl, fwhm, gain, offset, scene = _parse_metadata(meta_path)

    keep = np.ones(wl.size, dtype=bool)
    if wl_range is not None:
        keep &= (wl >= wl_range[0]) & (wl <= wl_range[1])
        if not keep.any():
            raise ValueError(f"no DESIS bands in {wl_range[0]}-{wl_range[1]} nm "
                             f"(sensor covers {wl.min():.0f}-{wl.max():.0f} nm)")
    idx = np.flatnonzero(keep)

    import rioxarray  # noqa: F401

    with rasterio.open(path) as src:
        if src.count != wl.size:
            raise ValueError(f"{src.count} raster bands but {wl.size} in the metadata")
        crs = src.crs
        transform = src.transform
        ny, nx = src.height, src.width
    # Lazy, in full-width row strips: the GeoTIFF writer streams those straight
    # into band-interleaved strips, and a spatial window reads only its rows.
    cube = rioxarray.open_rasterio(path, chunks={"band": -1, "y": 256, "x": -1})
    cube = cube.isel(band=idx).astype("float32")
    cube = cube.where(cube != NODATA)
    if apply_scale:
        # Per-band on L1B/L1C; a scene-wide factor would be wrong there.
        cube = cube * xr.DataArray(gain[keep], dims="band") + xr.DataArray(offset[keep], dims="band")
    cube = (cube.drop_vars(list(cube.coords), errors="ignore")
                .transpose("y", "x", "band").rename({"band": "wavelength"}))

    ds = xr.Dataset(
        {var: cube},
        coords={"wavelength": ("wavelength", wl[keep]),
                "fwhm": ("wavelength", fwhm[keep])},
        attrs={
            "sensor": "DESIS", "level": level,
            "granule": path.name.replace("-SPECTRAL_IMAGE.tif", ""),
            "units": units if apply_scale else "DN",
            "orthorectified": int(level in ("L1C", "L2A")),
            "mission_note": "DESIS operations ended 2023-12-31; archive only",
            **scene,
        },
    )
    ds["wavelength"].attrs.update(units="nm", long_name="band centre")
    ds["fwhm"].attrs.update(units="nm", long_name="band width")
    ds[var].attrs.update(units=ds.attrs["units"], long_name=long_name)

    if crs is not None:
        ds.attrs["crs"] = crs_text(crs)
        # GDAL order (originX, pixW, rotX, originY, rotY, pixH) - the package-wide
        # convention. rasterio's Affine uses a different order; mixing them
        # silently reinterprets pixel size as an origin.
        ds.attrs["transform"] = tuple(transform.to_gdal())
        ds.coords["x"] = ("x", transform.c + (np.arange(nx) + 0.5) * transform.a)
        ds.coords["y"] = ("y", transform.f + (np.arange(ny) + 0.5) * transform.e)
        ds["x"].attrs.update(units="m", standard_name="projection_x_coordinate")
        ds["y"].attrs.update(units="m", standard_name="projection_y_coordinate")

    if quality:
        _add_quality(ds, path)
    if band_quality:
        _add_band_quality(ds, path, idx)
    finish_bands(ds, index=idx, fill_value=NODATA)
    normalise_angles(ds)
    return ds


# --------------------------------------------------------------- metadata


def _sibling(path: Path, suffix: str) -> Path | None:
    stem = re.sub(r"-SPECTRAL_IMAGE\.tif$", "", path.name, flags=re.I)
    cand = path.with_name(f"{stem}-{suffix}")
    return cand if cand.exists() else None


def _parse_metadata(path: Path):
    """Wavelengths, FWHM, per-band gain/offset and the scene-level scalars.

    ``<band>`` appears under two parents in DESIS metadata - ``bandCharacterisation``
    (spectral) and ``interiorOrientation`` (geometric) - so the search is scoped
    to the former. Reading them unscoped silently doubles the band count.
    """
    root = ET.parse(path).getroot()
    bc = next(root.iter("bandCharacterisation"), None)
    if bc is None:
        raise ValueError(f"{path.name} has no <bandCharacterisation>")

    wl, fwhm, gain, off = [], [], [], []
    for b in bc.iter("band"):
        wl.append(float(b.findtext("wavelengthCenterOfBand")))
        fwhm.append(float(b.findtext("wavelengthWidthOfBand")))
        gain.append(float(b.findtext("gainOfBand")))
        off.append(float(b.findtext("offsetOfBand")))

    scene = {}
    for tag, name in SCENE_TAGS.items():
        v = root.findtext(f".//{tag}")
        if v is not None:
            try:
                scene[name] = float(v)
            except ValueError:
                scene[name] = v.strip()
    for tag, name in (("startTime", "datetime"), ("endTime", "datetime_end")):
        v = root.findtext(f".//{tag}")
        if v:
            scene[name] = v.strip()
    # DESIS reports no view azimuth. The L1B sceneAzimuthAngle is the flight
    # heading (ascending ISS passes head north-east); the pointing mirror tilts
    # along track by fractions of a degree here, so the off-nadir view is
    # taken as across track, to the right of the heading. Relative azimuth
    # enters the radiative transfer only through the aerosol phase function.
    # L1C/L2A report the across-track direction to the left instead (the same
    # acquisition gives 36.3 on L1B and 307.9 on L1C), so there the same
    # physical direction is sceneAzimuthAngle + 180.
    if "scene_azimuth_angle" in scene and "view_azimuth" not in scene:
        offset = 90.0 if "-L1B-" in Path(path).name else 180.0
        try:
            scene["view_azimuth"] = float(np.mod(float(scene["scene_azimuth_angle"]) + offset, 360.0))
            scene["view_azimuth_source"] = ("assumed across-track, right of the flight heading "
                                            f"(sceneAzimuthAngle + {offset:g} on this level)")
        except (TypeError, ValueError):
            pass

    return (np.asarray(wl, "float64"), np.asarray(fwhm, "float64"),
            np.asarray(gain, "float32"), np.asarray(off, "float32"), scene)


def _add_quality(ds: xr.Dataset, path: Path) -> None:
    """The 10-band L2A quality raster. L1B/L1C do not ship one."""
    import rasterio

    src_path = _sibling(path, "QL_QUALITY-2.tif")
    if src_path is None:
        return
    with rasterio.open(src_path) as src:
        arr = src.read()                                   # (band, y, x)
    if arr.shape[1:] != (ds.sizes["y"], ds.sizes["x"]):
        return
    for name, i in QUALITY_FLAGS.items():
        ds[name] = (("y", "x"), arr[i] > 0)
        ds[name].attrs["long_name"] = f"{name.replace('_', ' ')} flag"
    ds["cloud"] = (("y", "x"), (arr[QUALITY_FLAGS["cloud_land"]] > 0)
                   | (arr[QUALITY_FLAGS["cloud_water"]] > 0))
    ds["cloud"].attrs["long_name"] = "cloud over land or water"
    for name, (i, scale) in QUALITY_VALUES.items():
        ds[name] = (("y", "x"), arr[i].astype("float32") * scale)
    ds["aot550"].attrs.update(long_name="aerosol optical thickness at 550 nm")
    ds["wv_cm"].attrs.update(units="cm", long_name="column water vapour")
    ds.attrs["quality_source"] = src_path.name


def _add_band_quality(ds: xr.Dataset, path: Path, idx: np.ndarray) -> None:
    import rasterio

    src_path = _sibling(path, "QL_QUALITY.tif")
    if src_path is None:
        return
    with rasterio.open(src_path) as src:
        if src.count < int(idx.max()) + 1:
            return
        arr = src.read([int(i) + 1 for i in idx])
    ds["band_quality"] = (("y", "x", "wavelength"), np.moveaxis(arr, 0, -1))
    ds["band_quality"].attrs["long_name"] = "per-band quality flag"
