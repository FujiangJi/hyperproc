"""EnMAP (DLR/GFZ) reader for L1B / L1C / L2A GeoTIFF products.

224 bands, 418-2445 nm, 30 m, from a VNIR (91 bands) and a SWIR (133 bands)
spectrometer that overlap around 902-993 nm.

Three things differ from the other sensors here:

1. **L1B is two detectors on two grids, and stays that way here.** DLR ships
   ``SPECTRAL_IMAGE_VNIR`` and ``SPECTRAL_IMAGE_SWIR`` as separate files - and,
   tellingly, separate per-detector quality and pixel-mask products too - because
   at L1B the two focal planes have not been co-registered; that alignment is
   what the L1C geometric processing does. Stacking the two arrays by pixel
   index would produce a tidy 224-band cube whose spectra do not all come from
   the same ground spot, so the reader returns **one detector at a time** and
   refuses ``cube="full"`` on L1B. Both TIFs carry an identical EPSG:4326
   affine; it is a scene-level corner fit (about 34 x 32 m implied pixels), not a
   georeference, so it is kept as ``attrs["approx_geocoding_gdal"]`` and **not**
   as ``crs``/``transform`` - ``to_geotiff`` refuses an L1B cube, as it does
   for DESIS L1B. L1C and L2A ship one merged, co-registered 224-band file.
2. **Angles are given per scene corner**, not as a scalar or a raster. Viewing
   zenith runs 20.1 to 22.7 degrees across this scene, so the reader bilinearly
   interpolates the four corners into a real per-pixel grid. The corner values
   themselves stay in ``ds.attrs``.
3. **The sun angle is an elevation, not a zenith.** It is converted here
   (``sza = 90 - elevation``) so it matches every other reader.

Scaling is ``value = DN * GainOfBand + OffsetOfBand``. L2A uses a uniform gain
of 1e-4 with zero offset; **L1B and L1C carry a per-band gain and offset**.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import warnings

import numpy as np

from hyperproc.readers._common import crs_text, finish_bands, normalise_angles
import xarray as xr

#: Product level -> (variable, units, long name, nodata).
LEVEL_SPEC = {
    "L1B": ("radiance", "W/m^2/sr/nm", "at-sensor TOA radiance", 0),
    "L1C": ("radiance", "W/m^2/sr/nm", "at-sensor TOA radiance, orthorectified", 0),
    "L2A": ("reflectance", "1", "surface reflectance", -32768),
}

#: Single-band quality rasters shipped beside the cube.
QUALITY_LAYERS = {
    "cloud": "QL_QUALITY_CLOUD", "cloudshadow": "QL_QUALITY_CLOUDSHADOW",
    "cirrus": "QL_QUALITY_CIRRUS", "haze": "QL_QUALITY_HAZE",
    "snow": "QL_QUALITY_SNOW", "classes": "QL_QUALITY_CLASSES",
    "testflags": "QL_QUALITY_TESTFLAGS",
}

#: XML angle element -> our name. Each holds four corners plus a centre.
ANGLE_TAGS = {
    "sunAzimuthAngle": "saa", "viewingZenithAngle": "vza",
    "viewingAzimuthAngle": "vaa", "sceneAzimuthAngle": "scene_azimuth",
    "acrossOffNadirAngle": "across_off_nadir", "alongOffNadirAngle": "along_off_nadir",
}
_CORNERS = ("upper_left", "upper_right", "lower_right", "lower_left")

_GRANULE = re.compile(
    r"^ENMAP01-_*(?P<level>L1B|L1C|L2A)-(?P<rest>.+?)-SPECTRAL_IMAGE"
    r"(?:_(?P<arm>VNIR|SWIR))?(?:_COG)?\.TIF$", re.IGNORECASE)


def _beside(path: Path, name: str) -> Path:
    """The sibling ``name``, or DLR's cloud-optimised spelling of it.

    The EOC Geoservice publishes every raster twice over: the plain GeoTIFF the
    order form delivers, and a ``_COG`` copy, which is what the STAC catalogue
    links and therefore what :func:`hyperproc.search` downloads. They hold the
    same bands, so accepting both here means a searched granule opens without
    anyone renaming files. Returns the plain name when neither exists, so the
    caller's "missing" message names the file people expect.
    """
    plain = path.with_name(name)
    if plain.exists():
        return plain
    stem, _, ext = name.rpartition(".")
    cog = path.with_name(f"{stem}_COG.{ext}")
    return cog if cog.exists() else plain


def open_enmap(
    path: str | Path,
    cube: str | None = None,
    wl_range: tuple[float, float] | None = None,
    quality: bool = True,
    pixelmask: bool = False,
    angles: bool = True,
    apply_scale: bool = True,
) -> xr.Dataset:
    """Open an EnMAP granule.

    Args:
        path: the ``*-SPECTRAL_IMAGE.TIF``, or for L1B one of
            ``*-SPECTRAL_IMAGE_VNIR.TIF`` / ``*_SWIR.TIF``. DLR's cloud-optimised
            copies, ``*_COG.TIF``, are read the same way and find their
            ``_COG`` siblings.
        cube: L1B only. ``"vnir"`` (91 bands, 418-993 nm) or ``"swir"`` (133
            bands, 902-2445 nm); the default follows the file you passed.
            ``"full"`` raises on L1B - the detectors are not co-registered until
            L1C, so a merged L1B cube would mix ground locations band to band.
            L1C and L2A always ship one merged cube and ignore this.
        wl_range: ``(min_nm, max_nm)`` band subset.
        quality: attach the single-band quality rasters - ``cloud``,
            ``cloudshadow``, ``cirrus``, ``haze``, ``snow``, ``classes``,
            ``testflags``.
        pixelmask: attach the per-band pixel mask as ``pixelmask``
            ``(y, x, wavelength)``, lazy and band-aligned with the cube (same
            detector, order and ``wl_range``).
            Adds a uint8 array the size of the cube.
        angles: interpolate the corner angles into per-pixel ``sza``, ``saa``,
            ``vza``, ``vaa`` grids.
        apply_scale: apply the per-band gain and offset. ``False`` gives raw DN.

    Returns:
        Dataset with ``radiance`` or ``reflectance`` on ``(y, x, wavelength)``.
    """
    import rasterio

    path = Path(path)
    m = _GRANULE.match(path.name)
    if m is None:
        raise ValueError(
            f"{path.name} is not an EnMAP spectral image "
            f"(expected ENMAP01-____<L1B|L1C|L2A>-*-SPECTRAL_IMAGE[_VNIR|_SWIR].TIF, "
            f"or the _COG spelling the DLR STAC catalogue links)"
        )
    level = m.group("level").upper()
    var, units, long_name, nodata = LEVEL_SPEC[level]
    stem = f"ENMAP01-____{level}-{m.group('rest')}"

    meta = _beside(path, f"{stem}-METADATA.XML")
    if not meta.exists():
        raise FileNotFoundError(
            f"{path.name} needs its METADATA.XML sibling - EnMAP GeoTIFFs carry "
            f"no wavelengths or scaling of their own."
        )
    wl, fwhm, gain, offset, scene, n_vnir = _parse_metadata(meta)

    # L1B is two detectors on two grids; L1C/L2A are one co-registered cube.
    approx_geo = None
    if level == "L1B":
        arm = (cube or (m.group("arm") or "vnir")).lower()
        if arm == "full":
            raise ValueError(
                "EnMAP L1B VNIR and SWIR are not co-registered - the two focal "
                "planes are aligned in the L1C geometric processing, and DLR ships "
                "L1B quality and pixel masks per detector for that reason. Stacking "
                "them by pixel index would give spectra whose bands come from "
                "different ground spots. Open one detector, cube='vnir' or "
                "cube='swir', or use the L1C product for a merged cube.")
        if arm not in ("vnir", "swir"):
            raise ValueError(f"cube must be 'vnir' or 'swir' for L1B, not {cube!r}")
        f = _beside(path, f"{stem}-SPECTRAL_IMAGE_{arm.upper()}.TIF")
        if not f.exists():
            raise FileNotFoundError(f"missing {f.name}")
        with rasterio.open(f) as src:
            ny, nx = src.height, src.width
            # The TIF's EPSG:4326 affine is a corner fit shared by both
            # detectors, not a georeference; keep it, but not where to_geotiff
            # would treat it as one.
            approx_geo = (str(src.crs), tuple(src.transform.to_gdal()))
        data = _lazy_cube(f)
        crs = transform = None
        idx = np.arange(len(wl))[slice(0, n_vnir) if arm == "vnir" else slice(n_vnir, None)]
        cube = arm
    else:
        with rasterio.open(path) as src:
            crs, transform, ny, nx = src.crs, src.transform, src.height, src.width
        data = _lazy_cube(path)
        idx = np.arange(len(wl))

    w, f_, g, o = wl[idx], fwhm[idx], gain[idx], offset[idx]
    order = np.argsort(w)                       # L1B VNIR+SWIR interleave here
    data, w, f_, g, o = data.isel(band=order), w[order], f_[order], g[order], o[order]
    bidx = idx[order]                           # position in the source band list

    if wl_range is not None:
        keep = (w >= wl_range[0]) & (w <= wl_range[1])
        if not keep.any():
            raise ValueError(f"no EnMAP bands in {wl_range[0]}-{wl_range[1]} nm "
                             f"(sensor covers {wl.min():.0f}-{wl.max():.0f} nm)")
        data, w, f_, g, o = data.isel(band=keep), w[keep], f_[keep], g[keep], o[keep]
        bidx = bidx[keep]

    data = data.where(data != nodata)
    if apply_scale:
        data = data * xr.DataArray(g, dims="band") + xr.DataArray(o, dims="band")
    data = data.transpose("y", "x", "band").rename({"band": "wavelength"})

    ds = xr.Dataset(
        {var: data},
        coords={"wavelength": ("wavelength", w), "fwhm": ("wavelength", f_)},
        attrs={"sensor": "EnMAP", "level": level, "granule": stem,
               # L1B VNIR and SWIR are separate cubes of one granule: give each
               # its own stem so exporting both does not overwrite one file.
               "stem": f"{stem}_{cube.lower()}" if level == "L1B" and cube != "full" else stem,
               "units": units if apply_scale else "DN",
               "orthorectified": int(level in ("L1C", "L2A")),
               "cube": cube if level == "L1B" else "full", **scene},
    )
    if level == "L1B":
        ds.attrs.update(grid="sensor", detector=cube,
                        approx_geocoding_crs=approx_geo[0],
                        approx_geocoding_gdal=approx_geo[1],
                        approx_geocoding_note="scene-level corner fit shared by both "
                                              "detectors; ~34x32 m implied pixels, not a "
                                              "georeference - use L1C/L2A for mapping")
    ds["wavelength"].attrs.update(units="nm", long_name="band centre")
    ds["fwhm"].attrs.update(units="nm", long_name="band width")
    ds[var].attrs.update(units=ds.attrs["units"], long_name=long_name)

    if crs is not None:
        ds.attrs["crs"] = crs_text(crs)
        ds.attrs["transform"] = tuple(transform.to_gdal())   # GDAL order, package-wide
        ds.coords["x"] = ("x", transform.c + (np.arange(nx) + 0.5) * transform.a)
        ds.coords["y"] = ("y", transform.f + (np.arange(ny) + 0.5) * transform.e)

    if angles:
        _add_angles(ds, meta, ny, nx, crs, transform)
    if quality:
        _add_quality(ds, path, stem, ny, nx)
    if pixelmask:
        _add_pixelmask(ds, path, stem, level, bidx, n_vnir)
    finish_bands(ds, index=bidx, fill_value=nodata)
    normalise_angles(ds)
    return ds


# --------------------------------------------------------------- metadata


def _lazy_cube(path: Path) -> xr.DataArray:
    """The GeoTIFF as a lazy (band, y, x) float32 array in full-width row strips."""
    import rioxarray  # noqa: F401
    da = rioxarray.open_rasterio(path, chunks={"band": -1, "y": 256, "x": -1})
    return da.drop_vars(list(da.coords), errors="ignore").astype("float32")


def _parse_metadata(path: Path):
    root = ET.parse(path).getroot()
    bands = list(next(root.iter("bandCharacterisation")).iter("bandID"))
    wl = np.array([float(b.findtext("wavelengthCenterOfBand")) for b in bands])
    fwhm = np.array([float(b.findtext("FWHMOfBand")) for b in bands])
    gain = np.array([float(b.findtext("GainOfBand")) for b in bands], dtype="float32")
    off = np.array([float(b.findtext("OffsetOfBand")) for b in bands], dtype="float32")

    scene = {}
    for tag, name in ANGLE_TAGS.items():
        e = next(root.iter(tag), None)
        if e is not None and e.findtext("center"):
            scene[f"{name}_center"] = float(e.findtext("center"))
    el = next(root.iter("sunElevationAngle"), None)
    if el is not None and el.findtext("center"):
        # Every other reader reports a zenith; EnMAP reports an elevation.
        scene["sza_center"] = 90.0 - float(el.findtext("center"))
        scene["sun_elevation_center"] = float(el.findtext("center"))
    for tag, name in (("startTime", "datetime"), ("stopTime", "datetime_end"),
                      ("cloudCover", "cloud_cover_pct"),
                      ("cloudShadow", "cloud_shadow_pct")):
        v = root.findtext(f".//{tag}")
        if v and v.strip():
            try:
                scene[name] = float(v)
            except ValueError:
                scene[name] = v.strip()
    n_vnir = int(root.findtext(".//numberOfVNIRBands") or 91)
    return wl, fwhm, gain, off, scene, n_vnir


def _corner_grid(c: dict, ny: int, nx: int) -> np.ndarray:
    """Bilinear fill of a scene from its four corner values."""
    ul, ur, lr, ll = (float(c[k]) for k in _CORNERS)
    xx = np.linspace(0.0, 1.0, nx)[None, :]
    yy = np.linspace(0.0, 1.0, ny)[:, None]
    top = ul + (ur - ul) * xx
    bot = ll + (lr - ll) * xx
    return (top + (bot - top) * yy).astype("float32")


def _footprint_pixels(root, crs, transform, ny: int, nx: int):
    """Pixel (col, row) of the four footprint corners, in _CORNERS order, or None.

    The angle corners in the XML belong to the *footprint* (``boundingPolygon``
    of ``spatialCoverage``), which on the north-up L1C/L2A raster is a rotated
    quadrilateral inside the box, not the box's corners.
    """
    if crs is None or transform is None:
        return None
    poly = next(root.iter("boundingPolygon"), None)
    if poly is None:
        return None
    pts = {}
    for pt in poly.iter("point"):
        frame, lat, lon = pt.findtext("frame"), pt.findtext("latitude"), pt.findtext("longitude")
        if frame and lat and lon and frame.strip() in _CORNERS and frame.strip() not in pts:
            pts[frame.strip()] = (float(lon), float(lat))
    if len(pts) < 4:
        return None
    from pyproj import Transformer
    tf = Transformer.from_crs(4326, crs, always_xy=True)
    inv = ~transform
    out = []
    for k in _CORNERS:
        e, n = tf.transform(*pts[k])
        col, row = inv @ (e, n)
        out.append((float(col), float(row)))
    return out


def _footprint_grid(c: dict, corners, ny: int, nx: int) -> np.ndarray:
    """Plane through the four footprint-corner values, NaN outside the footprint.

    Corner angles vary linearly across a scene to well under 0.1 deg, so a
    least-squares plane on (col, row) reproduces the given corner values and,
    unlike a bilinear fill of the raster box, puts them where the footprint
    corners actually are (0.55 deg error at the corners otherwise).
    """
    vals = np.array([float(c[k]) for k in _CORNERS])
    cr = np.array(corners)                                  # (4, 2) col,row at pixel corners
    A = np.column_stack([np.ones(4), cr[:, 0], cr[:, 1]])
    coef, *_ = np.linalg.lstsq(A, vals, rcond=None)
    cols = np.arange(nx) + 0.5
    rows = np.arange(ny) + 0.5
    grid = coef[0] + coef[1] * cols[None, :] + coef[2] * rows[:, None]
    # inside the (convex) footprint quadrilateral: same side of every edge
    inside = np.ones((ny, nx), dtype=bool)
    for i in range(4):
        (x0, y0), (x1, y1) = cr[i], cr[(i + 1) % 4]
        cross = (x1 - x0) * (rows[:, None] - y0) - (y1 - y0) * (cols[None, :] - x0)
        inside &= cross <= 1e-9 if _signed_area(cr) < 0 else cross >= -1e-9
    return np.where(inside, grid, np.nan).astype("float32")


def _signed_area(cr: np.ndarray) -> float:
    x, y = cr[:, 0], cr[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _add_angles(ds: xr.Dataset, meta: Path, ny: int, nx: int, crs=None, transform=None) -> None:
    root = ET.parse(meta).getroot()
    corners = _footprint_pixels(root, crs, transform, ny, nx)
    fill = (lambda c: _footprint_grid(c, corners, ny, nx)) if corners else (lambda c: _corner_grid(c, ny, nx))
    how = "plane through the footprint corners, NaN outside" if corners else "bilinear over the sensor grid"
    for tag, name in ANGLE_TAGS.items():
        e = next(root.iter(tag), None)
        if e is None:
            continue
        c = {k.tag: k.text for k in e}
        if not all(k in c and c[k] for k in _CORNERS):
            continue
        ds[name] = (("y", "x"), fill(c))
        ds[name].attrs.update(units="degrees", long_name=f"{tag} ({how})")
    e = next(root.iter("sunElevationAngle"), None)
    if e is not None:
        c = {k.tag: k.text for k in e}
        if all(k in c and c[k] for k in _CORNERS):
            ds["sza"] = (("y", "x"), 90.0 - fill(c))
            ds["sza"].attrs.update(units="degrees",
                                   long_name=f"solar zenith (90 - sunElevationAngle; {how})")


def _add_quality(ds: xr.Dataset, path: Path, stem: str, ny: int, nx: int) -> None:
    import rasterio

    for name, suffix in QUALITY_LAYERS.items():
        if name == "testflags" and ds.attrs.get("level") == "L1B":
            suffix = f"{suffix}_{ds.attrs['detector'].upper()}"   # per detector at L1B
        f = _beside(path, f"{stem}-{suffix}.TIF")
        if not f.exists():
            continue
        with rasterio.open(f) as src:
            if (src.height, src.width) != (ny, nx):
                continue
            a = src.read(1)
        ds[name] = (("y", "x"), a > 0) if name not in ("classes", "testflags") \
            else (("y", "x"), a)
        ds[name].attrs["long_name"] = suffix.lower()


def _add_pixelmask(ds: xr.Dataset, path: Path, stem: str, level: str, bidx: np.ndarray, n_vnir: int) -> None:
    """Per-band pixel mask, lazily, on the cube's own band axis.

    The mask file has one band per spectral band of the *file* it belongs to,
    so the cube's source band positions (``bidx``) index it directly at
    L1C/L2A; at L1B only the opened detector's mask applies, and the SWIR
    positions are offset by the VNIR band count.
    """
    import rioxarray  # noqa: F401

    if level == "L1B":
        det = str(ds.attrs.get("detector", "vnir")).lower()
        suffix, local = f"QL_PIXELMASK_{det.upper()}", bidx - (0 if det == "vnir" else n_vnir)
    else:
        suffix, local = "QL_PIXELMASK", bidx
    f = _beside(path, f"{stem}-{suffix}.TIF")
    if not f.exists():
        warnings.warn(f"{path.name}: no {suffix} file next to it; pixelmask not attached")
        return
    m = rioxarray.open_rasterio(f, chunks={"band": -1, "y": 256, "x": -1})
    if int(local.max()) >= m.sizes["band"]:
        warnings.warn(f"{f.name}: {m.sizes['band']} mask bands but the cube refers to band "
                      f"{int(local.max())}; pixelmask not attached")
        return
    m = m.drop_vars(list(m.coords), errors="ignore").isel(band=local)
    ds["pixelmask"] = m.transpose("y", "x", "band").rename({"band": "wavelength"})
    ds["pixelmask"].attrs.update(long_name=f"per-band pixel mask ({suffix.lower()}), aligned with the cube")
