"""PRISMA (ASI) reader for L1 / L2B / L2C / L2D HDF-EOS5 granules.

A Python port of the parts of `prismaread <https://github.com/irea-cnr-mi/prismaread>`_
(``pr_convert``) that matter for analysis. Four things about the format catch
people out, and this module handles all of them:

1. **Cubes are stored band-interleaved**, shaped ``(rows, bands, cols)``, not
   ``(rows, cols, bands)``. Reading them naively transposes your image.
2. **Wavelengths run descending** in both spectrometers - the first VNIR band
   is ~977 nm, the last ~407 nm. They are flipped to ascending here.
3. **Some bands are not acquired at all** and carry a centre wavelength of
   exactly ``0.0``, flagged in ``List_Cw_*_Flags``. On this granule that is
   3 VNIR and 2 SWIR bands. They are dropped - a 0 nm band is not data.
4. **VNIR and SWIR overlap** around 943-977 nm. ``join_priority`` decides which
   spectrometer wins there, matching prismaread's argument of the same name.

DN are stored as ``uint16`` and rescaled per spectrometer. L2 uses a min/max
stretch, L1 a factor and offset::

    L2:  value = ScaleMin + DN * (ScaleMax - ScaleMin) / 65535
    L1:  value = DN / ScaleFactor - Offset            (W m-2 sr-1 um-1)

L1 ships no per-pixel angles and no elevation. When the L2C (or L2B) file of
the same acquisition sits beside it, its ``Geometric Fields`` and its refined
geolocation are borrowed (``angles_source="l2"``, the default); otherwise the
view angles are computed from the satellite ephemeris in the file and the sun
angles are the scene-level values. Elevation is left to
:func:`hyperproc.atmos.dem.add_elevation`.

Levels differ in geometry, not in cube layout:

=======  ===================================  ==========================
level    grid                                 georeferencing
=======  ===================================  ==========================
L1       1000 x 1000 swath, TOA radiance      lat/lon arrays
L2B      1000 x 1000 swath, surface radiance  lat/lon arrays
L2C      1000 x 1000 swath, reflectance       lat/lon arrays
L2D      n x m UTM grid, reflectance          EPSG + affine transform
=======  ===================================  ==========================
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from hyperproc.readers._common import finish_bands, normalise_angles
import xarray as xr

DN_MAX = 65535.0

#: Product level -> (cube variable name, units, long name).
LEVEL_SPEC = {
    "L1": ("radiance", "W/m^2/sr/um", "at-sensor radiance"),
    "L2B": ("radiance", "W/m^2/sr/um", "at-surface radiance"),
    "L2C": ("reflectance", "1", "surface reflectance"),
    "L2D": ("reflectance", "1", "surface reflectance"),
}

#: Per-pixel angle datasets under ``Geometric Fields`` -> our names.
ANGLE_FIELDS = {"sza": "Solar_Zenith_Angle", "vza": "Observing_Angle",
                "raa": "Rel_Azimuth_Angle"}

#: Extra L2C maps, each its own HDF-EOS swath, with its own scale attributes.
L2C_MAPS = {"aot": ("AOT", "AOT_Map"), "aex": ("AEX", "AEX_Map"),
            "cot": ("COT", "COT_Map"), "wvm": ("WVM", "WVM_Map")}

_GRANULE = re.compile(r"^PRS_(?P<level>L1|L2B|L2C|L2D)_(?P<type>\w+?)_(?P<rest>.+)\.he5$",
                      re.IGNORECASE)


def open_prisma(
    path: str | Path,
    cube: str = "full",
    join_priority: str = "swir",
    wl_range: tuple[float, float] | None = None,
    good_bands_only: bool = False,
    angles: bool = True,
    latlon: bool = False,
    err_matrix: bool = False,
    extras: bool = True,
    angles_source: str = "l2",
    geolocation: str = "l2",
) -> xr.Dataset:
    """Open a PRISMA granule.

    Args:
        path: ``PRS_<level>_STD_*.he5``.
        cube: ``"full"`` merges both spectrometers, ``"vnir"`` (~407-977 nm) or
            ``"swir"`` (~943-2497 nm) returns one alone.
        join_priority: which spectrometer wins in the ~943-977 nm overlap when
            ``cube="full"``. ``"swir"`` (prismaread's default here) or ``"vnir"``.
        wl_range: ``(min_nm, max_nm)`` subset, applied after the join.
        good_bands_only: not supported - ASI ships no per-band quality flag.
            Raises, with a pointer to ``wl_range``.
        angles: attach per-pixel ``sza``, ``vza``, ``raa`` (degrees).
        latlon: attach the per-pixel ``lat``/``lon`` arrays. Always attached for
            L1/L2B/L2C, where they are the only georeferencing there is.
        err_matrix: attach the per-band pixel error matrix, band-aligned with
            the cube (same subset, order and overlap resolution), lazy uint8:
            ``l2_err`` for L2 (0 = no error flag), ``l1_sat_err`` for L1
            (0 ok, 1 saturated, 2 error, 3 both). Adds a uint8 array the size
            of the cube.
        extras: for L2C, attach the AOT / AEX / COT / WVM maps.
        angles_source: L1 only. ``"l2"`` borrows the per-pixel angles from an
            L2C/L2B file of the same acquisition beside the L1 when there is
            one, else falls back to ``"ephemeris"`` (view angles from the
            satellite positions in the file, sun angles scene-level).
        geolocation: L1 only. ``"l2"`` uses the L2C/L2B geolocation (ASI
            refines it during L2 processing; it differs from L1's by up to a
            few pixels), ``"l1"`` keeps the L1 arrays.

    Returns:
        Dataset with ``reflectance`` or ``radiance`` on ``(y, x, wavelength)``,
        ``wavelength`` and ``fwhm`` coordinates in nm, ascending.
    """
    import h5py

    path = Path(path)
    m = _GRANULE.match(path.name)
    if m is None:
        raise ValueError(f"{path.name} is not a PRISMA granule (expected PRS_<level>_*.he5)")
    if cube not in ("full", "vnir", "swir"):
        raise ValueError(f"cube must be 'full', 'vnir' or 'swir', got {cube!r}")
    if join_priority.lower() not in ("swir", "vnir"):
        raise ValueError(f"join_priority must be 'swir' or 'vnir', got {join_priority!r}")
    if good_bands_only:
        raise ValueError(
            "good_bands_only is not available for PRISMA - ASI ships no per-band "
            "quality flag (unlike EMIT's good_wavelengths). Bands never acquired "
            "are dropped automatically. Use wl_range=, or mask the water-vapour "
            "windows yourself with .where() on the wavelength coordinate."
        )

    with h5py.File(path, "r") as f:
        level = f.attrs["Processing_Level"]
        level = f"L{level.decode() if isinstance(level, bytes) else level}".upper()
        if level not in LEVEL_SPEC:
            raise ValueError(f"unsupported PRISMA level {level!r}")
        var, units, long_name = LEVEL_SPEC[level]
        swath = f"HDFEOS/SWATHS/PRS_{level}_HCO"

        parts = [_read_arm(f, swath, a, err=err_matrix)
                 for a in (("vnir", "swir") if cube == "full" else (cube,))]
        if len(parts) == 2:
            parts = _resolve_overlap(parts, join_priority.lower())

        def cat(i):
            return xr.concat([p[i] for p in parts], dim="wavelength") if len(parts) > 1 else parts[0][i]
        err = cat(5) if err_matrix and all(p[5] is not None for p in parts) else None
        part = (cat(0), *[np.concatenate([p[i] for p in parts]) for i in (1, 2, 3, 4)], err)

        order = np.argsort(part[1])                 # ascending, VNIR then SWIR
        data, wl, fwhm, arm, bidx, err = _take(part, order)

        # L2D is resampled into a north-up UTM box, so the corners outside the
        # rotated swath are padded with exact 0 - about a third of this granule.
        # Left alone they read as very dark land and drag every statistic down.
        # The angle grid is zero on exactly the same pixels and is band
        # independent, so it is the reliable place to get the mask.
        fill = _fill_mask(f, swath) if level == "L2D" else None
        if fill is not None:
            data = data.where(~xr.DataArray(fill, dims=("y", "x")))

        if wl_range is not None:
            keep = (wl >= wl_range[0]) & (wl <= wl_range[1])
            if not keep.any():
                raise ValueError(f"no PRISMA bands in {wl_range[0]}-{wl_range[1]} nm")
            data, wl, fwhm, arm, bidx, err = _take((data, wl, fwhm, arm, bidx, err), keep)

        ds = xr.Dataset(
            {var: data},
            coords={"wavelength": ("wavelength", wl),
                    "fwhm": ("wavelength", fwhm),
                    "spectrometer": ("wavelength", arm)},
            attrs=_scene_attrs(f, path, level, units, cube, join_priority),
        )
        ds["wavelength"].attrs.update(units="nm", long_name="band centre")
        ds["fwhm"].attrs.update(units="nm", long_name="band width")
        ds[var].attrs.update(units=units, long_name=long_name)

        if fill is not None:
            ds["valid"] = (("y", "x"), ~fill)
            ds["valid"].attrs["long_name"] = "inside the acquired swath"

        _add_grid(ds, f, level, swath, latlon, fill)
        if level == "L1":
            _add_l1_masks(ds, f, swath)
            sib = _l2_sibling(path, m.group("rest"))
            if geolocation == "l2" and sib is not None:
                _borrow_geolocation(ds, sib)
            else:
                ds.attrs["geolocation_source"] = "L1 (VNIR arrays)"
            if angles:
                _add_l1_geometry(ds, f, sib if angles_source == "l2" else None)
        elif angles:
            _add_angles(ds, f, swath, fill)
        if err is not None:
            name = "l1_sat_err" if level == "L1" else "l2_err"
            ds[name] = err
            ds[name].attrs.update(long_name=("L1 saturation/error matrix, band-aligned with the cube (0 = ok, 1 = saturated, "
                                             "2 = error, 3 = both)" if level == "L1" else
                                             "L2 pixel error matrix, band-aligned with the cube (0 = no flag; also 0 on the L2D padding)"))
        if extras and level == "L2C":
            _add_l2c_maps(ds, f)
    finish_bands(ds, index=bidx, fill_value=0)
    ds["band_index"].attrs["long_name"] = "0-based band position within its spectrometer's cube (see 'spectrometer')"
    normalise_angles(ds)
    return ds


# ------------------------------------------------------------------ cubes


def _read_arm(f, swath: str, arm: str, err: bool = False):
    """Read one spectrometer: rescale, drop unacquired bands, fix axis order.

    Returns ``(data, wavelength, fwhm, arm_label, band_index, err)`` where
    ``err`` is the lazily read error matrix with the same band selection, or
    None. Every later selection (overlap, sort, wl_range) goes through
    :func:`_take` so the six stay aligned.
    """
    tag = arm.upper()
    cw = np.asarray(f.attrs[f"List_Cw_{arm.capitalize()}"], dtype="float64")
    fwhm = np.asarray(f.attrs[f"List_Fwhm_{arm.capitalize()}"], dtype="float64")
    flags = np.asarray(f.attrs[f"List_Cw_{arm.capitalize()}_Flags"], dtype=bool)

    # A band with centre wavelength 0.0 was never acquired.
    keep = flags & (cw > 0)
    l1 = f"L2Scale{arm.capitalize()}Min" not in f.attrs
    if l1:
        scale = float(f.attrs[f"ScaleFactor_{arm.capitalize()}"])
        offset = float(f.attrs[f"Offset_{arm.capitalize()}"])
    else:
        lo = float(f.attrs[f"L2Scale{arm.capitalize()}Min"])
        hi = float(f.attrs[f"L2Scale{arm.capitalize()}Max"])

    # Lazy: opened with xarray's lazy indexing, then chunked into row slabs -
    # the file stores the cube unchunked, so each slab is one contiguous read.
    fields = xr.open_dataset(f.filename, engine="h5netcdf", group=f"{swath}/Data Fields",
                             phony_dims="sort", decode_cf=False)
    raw = fields[f"{tag}_Cube"]                                          # (rows, bands, cols)
    raw = raw.rename({raw.dims[0]: "y", raw.dims[1]: "wavelength", raw.dims[2]: "x"})
    raw = raw.chunk({"y": 128, "wavelength": -1, "x": -1})
    sel = raw.isel(wavelength=keep)
    if l1:
        # L1 DN 0 is a real (tiny) radiance: the deep water bands and the
        # 2480-2500 nm edge round to 0 at ScaleFactor 100. Only a pixel with
        # every band at 0 is missing data. Masking single bands would hand
        # ISOFIT spectra with -9999 in some channels, which it inverts into
        # reflectances in the hundreds.
        data = sel.transpose("y", "x", "wavelength").astype("float32")
        data = data.where((sel != 0).any("wavelength"))
        data = data / scale - offset
    else:
        # L2 DN 0 is never a measurement (lo is 0): it marks a failed
        # retrieval in the absorption windows and the L2D padding. NaN, not 0.0.
        data = sel.where(sel != 0).transpose("y", "x", "wavelength").astype("float32")
        data = lo + data * ((hi - lo) / DN_MAX)

    e = None
    err_name = f"{tag}_PIXEL_SAT_ERR_MATRIX" if l1 else f"{tag}_PIXEL_L2_ERR_MATRIX"
    if err and err_name in fields:
        e = fields[err_name]
        e = e.rename({e.dims[0]: "y", e.dims[1]: "wavelength", e.dims[2]: "x"})
        e = e.chunk({"y": 128, "wavelength": -1, "x": -1}).isel(wavelength=keep).transpose("y", "x", "wavelength")
    return data, cw[keep], fwhm[keep], np.full(int(keep.sum()), arm, dtype=object), np.flatnonzero(keep), e


def _take(part, k):
    """Apply one band selection (mask or index array) to every element of a part."""
    data, wl, fwhm, arm, bidx, err = part
    return (data.isel(wavelength=k), wl[k], fwhm[k], arm[k], bidx[k],
            None if err is None else err.isel(wavelength=k))


def _resolve_overlap(parts, priority: str):
    """Drop the losing spectrometer's bands in the wavelength range both cover."""
    wv, ws = parts[0][1], parts[1][1]
    lo, hi = max(wv.min(), ws.min()), min(wv.max(), ws.max())
    if lo > hi:
        return parts                                  # no overlap
    if priority == "swir":
        return [_take(parts[0], ~((wv >= lo) & (wv <= hi))), parts[1]]
    return [parts[0], _take(parts[1], ~((ws >= lo) & (ws <= hi)))]


# --------------------------------------------------------------- metadata


def _dec(v):
    return v.decode() if isinstance(v, bytes) else v


def _scene_attrs(f, path: Path, level: str, units: str, cube: str, join: str) -> dict:
    a = f.attrs
    return {
        "sensor": "PRISMA",
        "level": level,
        "granule": path.stem,
        # vnir / swir subsets are different cubes of one granule: own stem each
        "stem": path.stem if cube == "full" else f"{path.stem}_{cube}",
        "datetime": _dec(a.get("Product_StartTime", b"")),
        "units": units,
        "cube": cube,
        "join_priority": join if cube == "full" else "",
        "orthorectified": int(level == "L2D"),
        "sun_zenith": float(a.get("Sun_zenith_angle", np.nan)),
        "sun_azimuth": float(a.get("Sun_azimuth_angle", np.nan)),
        "cloudy_pixels_pct": float(a.get("Cloudy_pixels_percentage", np.nan)),
        "sea_pixels_pct": float(a.get("Sea_pixels_percentage", np.nan)),
        "processor_version": _dec(a.get("L1_Processor_Version", a.get("Processor_Version", b""))),
    }


def _fill_mask(f, swath: str) -> np.ndarray | None:
    """(y, x) True where L2D padding sits outside the acquired swath."""
    key = f"{swath}/Geometric Fields/Solar_Zenith_Angle"
    return f[key][:] == 0 if key in f else None


def _add_grid(ds: xr.Dataset, f, level: str, swath: str, latlon: bool,
              fill: np.ndarray | None = None) -> None:
    """L2D gets a UTM affine grid; the swath levels get lat/lon arrays."""
    geo = f"{swath}/Geolocation Fields"
    if level == "L2D":
        a = f.attrs
        ny, nx = ds.sizes["y"], ds.sizes["x"]
        # Corner attributes are pixel *centres*, so n-1 intervals across.
        px = (float(a["Product_LRcorner_easting"]) - float(a["Product_ULcorner_easting"])) / (nx - 1)
        py = (float(a["Product_ULcorner_northing"]) - float(a["Product_LLcorner_northing"])) / (ny - 1)
        x0, y0 = float(a["Product_ULcorner_easting"]), float(a["Product_ULcorner_northing"])
        ds.attrs["crs"] = f"EPSG:{int(a['Epsg_Code'])}"
        ds.attrs["transform"] = (x0 - px / 2, px, 0.0, y0 + py / 2, 0.0, -py)
        ds.coords["x"] = ("x", x0 + np.arange(nx) * px)
        ds.coords["y"] = ("y", y0 - np.arange(ny) * py)
        ds["x"].attrs.update(units="m", standard_name="projection_x_coordinate")
        ds["y"].attrs.update(units="m", standard_name="projection_y_coordinate")
        if not latlon:
            return
    for name, field in (("lat", "Latitude"), ("lon", "Longitude")):
        if f"{geo}/{field}" not in f:                 # L1: one array per spectrometer (identical on HCO)
            field = f"{field}_VNIR"
        arr = f[f"{geo}/{field}"][:].astype("float32")
        if fill is not None:
            arr[fill] = np.nan
        ds[name] = (("y", "x"), arr)
        ds[name].attrs["units"] = "degrees_north" if name == "lat" else "degrees_east"


def _add_angles(ds: xr.Dataset, f, swath: str, fill: np.ndarray | None = None) -> None:
    grp = f.get(f"{swath}/Geometric Fields")
    if grp is None:
        return
    for name, field in ANGLE_FIELDS.items():
        if field in grp:
            arr = grp[field][:].astype("float32")
            if fill is not None:
                arr[fill] = np.nan
            ds[name] = (("y", "x"), arr)
            ds[name].attrs.update(units="degrees", long_name=field.replace("_", " ").lower())


L1_MASKS = {"cloud": ("Cloud_Mask", "cloud (ASI L1 mask: 1 = cloudy)"),
            "sunglint": ("SunGlint_Mask", "sun glint (ASI L1 mask: 1 = glint)"),
            "landcover": ("LandCover_Mask", "ASI L1 land cover class (0 water, 1 snow, 2 bare, 3 crops, 4 forest, 5 wetland, 6 urban)")}


def _add_l1_masks(ds: xr.Dataset, f, swath: str) -> None:
    grp = f[f"{swath}/Data Fields"]
    for name, (field, long_name) in L1_MASKS.items():
        if field not in grp:
            continue
        raw = grp[field][:]
        ds[name] = (("y", "x"), raw if name == "landcover" else (raw == 1))
        ds[name].attrs["long_name"] = long_name


def _l2_sibling(path: Path, rest: str) -> Path | None:
    """The L2C (else L2B) file of the same acquisition beside an L1 file."""
    core = re.sub(r"^(OFFL|NRT|RT)_", "", rest, flags=re.IGNORECASE)
    for lvl in ("L2C", "L2B"):
        for cand in sorted(path.parent.glob(f"PRS_{lvl}_*_{core}.he5")):
            return cand
    return None


def _borrow_geolocation(ds: xr.Dataset, sib: Path) -> None:
    import h5py
    with h5py.File(sib, "r") as g:
        swath = [k for k in g["HDFEOS/SWATHS"].keys() if k.endswith("_HCO")][0]
        geo = g[f"HDFEOS/SWATHS/{swath}/Geolocation Fields"]
        lat, lon = geo["Latitude"][:].astype("float32"), geo["Longitude"][:].astype("float32")
    if lat.shape != (ds.sizes["y"], ds.sizes["x"]):
        ds.attrs["geolocation_source"] = "L1 (VNIR arrays; L2 sibling grid differs)"
        return
    ds["lat"] = (("y", "x"), lat)
    ds["lon"] = (("y", "x"), lon)
    ds["lat"].attrs["units"], ds["lon"].attrs["units"] = "degrees_north", "degrees_east"
    ds.attrs["geolocation_source"] = f"{sib.name} (ASI L2 refined geolocation)"


def _add_l1_geometry(ds: xr.Dataset, f, sib: Path | None) -> None:
    """Per-pixel angles for L1: from the L2 sibling when given, else ephemeris + scene sun angles."""
    a = f.attrs
    saa = float(a["Sun_azimuth_angle"])
    sza = float(a["Sun_zenith_angle"])
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    if sib is not None:
        import h5py
        with h5py.File(sib, "r") as g:
            swath = [k for k in g["HDFEOS/SWATHS"].keys() if k.endswith("_HCO")][0]
            grp = g.get(f"HDFEOS/SWATHS/{swath}/Geometric Fields")
            if grp is not None and grp["Solar_Zenith_Angle"].shape == (ny, nx):
                ds["sza"] = (("y", "x"), grp["Solar_Zenith_Angle"][:].astype("float32"))
                ds["vza"] = (("y", "x"), grp["Observing_Angle"][:].astype("float32"))
                ra = grp["Rel_Azimuth_Angle"][:].astype("float32")
                ds["saa"] = (("y", "x"), np.full((ny, nx), saa, dtype="float32"))
                ds["vaa"] = (("y", "x"), np.mod(saa + ra, 360.0).astype("float32"))
                for k in ("sza", "vza", "saa", "vaa"):
                    ds[k].attrs.update(units="degrees")
                ds["vaa"].attrs["long_name"] = "view azimuth = scene sun azimuth + L2 relative azimuth"
                ds.attrs["angles_source"] = f"{sib.name} (Geometric Fields); sun azimuth scene-level"
                return
    vza, vaa = _view_from_ephemeris(f, ds)
    ds["vza"] = (("y", "x"), vza.astype("float32"))
    ds["vaa"] = (("y", "x"), vaa.astype("float32"))
    ds["vza"].attrs.update(units="degrees", long_name="view zenith from the satellite ephemeris")
    ds["vaa"].attrs.update(units="degrees", long_name="view azimuth from the satellite ephemeris")
    ds.attrs.update(sza=sza, saa=saa, angles_source="ephemeris (view) + scene-level sun angles")


def _view_from_ephemeris(f, ds: xr.Dataset):
    """View zenith/azimuth per pixel from the WGS-84 satellite positions in the file.

    Line times are spread linearly between the product start and stop times;
    the ephemeris (GPS seconds of day, 18 s ahead of UTC) is interpolated to
    them; the ground point is the pixel's lat/lon at sea level (elevation
    changes the angles by hundredths of a degree at 615 km).
    """
    from datetime import datetime
    from pyproj import Transformer
    base = "Info/Ancillary/PVSdata"
    pos = np.stack([f[f"{base}/Wgs84_pos_{c}"][:].astype("float64") for c in "xyz"], axis=1)
    t = f[f"{base}/GPS_Time_of_Last_Position"][:].astype("float64")
    good = np.isfinite(pos).all(axis=1) & (np.linalg.norm(pos, axis=1) > 6.4e6) & np.isfinite(t)
    pos, t = pos[good], t[good]
    order = np.argsort(t)
    pos, t = pos[order], t[order]

    def sod(raw):
        txt = _dec(raw)
        dt = datetime.strptime(txt[:19], "%Y-%m-%dT%H:%M:%S")
        frac = float("0." + txt.split(".")[1]) if "." in txt else 0.0
        return dt.hour * 3600 + dt.minute * 60 + dt.second + frac

    t0, t1 = sod(f.attrs["Product_StartTime"]) + 18.0, sod(f.attrs["Product_StopTime"]) + 18.0
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    tl = np.linspace(t0, t1, ny)
    sat = np.stack([np.interp(tl, t, pos[:, i]) for i in range(3)], axis=1)          # (ny, 3)
    lat = np.asarray(ds["lat"].values, "float64")
    lon = np.asarray(ds["lon"].values, "float64")
    tf = Transformer.from_crs(4979, 4978, always_xy=True)                             # lon/lat/h -> ECEF
    gx, gy, gz = tf.transform(lon, lat, np.zeros_like(lat))
    v = np.stack([sat[:, None, 0] - gx, sat[:, None, 1] - gy, sat[:, None, 2] - gz], axis=-1)
    v /= np.linalg.norm(v, axis=-1, keepdims=True)
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    east = np.stack([-np.sin(lo), np.cos(lo), np.zeros_like(lo)], axis=-1)
    north = np.stack([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)], axis=-1)
    up = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1)
    e, n, u = (v * east).sum(-1), (v * north).sum(-1), (v * up).sum(-1)
    vza = np.rad2deg(np.arccos(np.clip(u, -1, 1)))
    vaa = np.mod(np.rad2deg(np.arctan2(e, n)), 360.0)
    return vza, vaa


def _add_l2c_maps(ds: xr.Dataset, f) -> None:
    """AOT / Angstrom exponent / cloud optical thickness / water vapour."""
    for name, (tag, field) in L2C_MAPS.items():
        key = f"HDFEOS/SWATHS/PRS_L2C_{tag}/Data Fields/{field}"
        if key not in f:
            continue
        lo = float(f.attrs[f"L2Scale{tag}Min"])
        hi = float(f.attrs[f"L2Scale{tag}Max"])
        arr = lo + f[key][:].astype("float32") * ((hi - lo) / DN_MAX)
        dims = ("y", "x") if arr.shape == (ds.sizes["y"], ds.sizes["x"]) \
            else (f"{name}_y", f"{name}_x")
        ds[name] = (dims, arr)
        ds[name].attrs["long_name"] = field.replace("_", " ")
