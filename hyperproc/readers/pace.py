"""PACE OCI (NASA) reader for L1B and L2 SFREFL granules.

OCI is a very different instrument from the land imagers in this package: a
~1 km ocean-colour spectrometer on a wide swath. One granule here covers 25 to
49 degrees north and 119 to 84 degrees west - most of the continental US - so it
is a *global-scale* product, not a scene.

=======  ==========================  ==================  ===================
level    variable                    bands               geometry
=======  ==========================  ==================  ===================
L1B      ``rhot`` TOA reflectance    291 (blue+red+SWIR) full, in-file
L2       ``rhos`` surface reflectance 122                none - from L1B
=======  ==========================  ==================  ===================

Three things catch people out:

1. **L1B splits the detector into three arrays** - ``rhot_blue`` (119 bands,
   315-606 nm), ``rhot_red`` (163, 600-895 nm) and ``rhot_SWIR`` (9, 940-2258
   nm), which overlap slightly. They are read, concatenated and sorted here.
2. **L1B stores bands first**, ``(band, scan, pixel)``, not last. Reading it
   naively transposes the image.
3. **L2 carries *some* geometry.** ``scan_line_attributes/csol_z`` gives a
   per-scan-line centre solar zenith and ``navigation_data/tilt`` the OCI tilt
   (used to dodge sunglint); both are read here and broadcast across track. The
   full per-pixel ``saa``/``vza``/``vaa`` live only in the L1B granule for the
   same timestamp, which is located automatically when it sits alongside.
4. **Neither level ships FWHM.** The 5 nm hyperspectral sampling is used as a
   documented nominal; the SWIR bands get their real bandpass, which runs
   15-80 nm and is nothing like 5.

Both levels are swaths with per-pixel lat/lon and no CRS. Use
:func:`hyperproc.georeference` to put them on a grid; it defaults to EPSG:4326
here rather than a UTM zone, because the swath is far too wide for one.
"""

from __future__ import annotations

import re
from pathlib import Path

import warnings

import numpy as np

from hyperproc.readers._common import finish_bands, normalise_angles
import xarray as xr

FILL = -32767.0

#: OCI's hyperspectral bands are sampled every 5 nm and neither product ships a
#: per-band FWHM, so 5 nm is used as a documented nominal below 900 nm.
NOMINAL_FWHM_NM = 5.0

#: The SWIR bands are multispectral and much wider. Values are OCI's own
#: ``SWIR_bandpass``, which only the L1B granule carries.
SWIR_BANDPASS = {939.71: 45.0, 1038.32: 80.0, 1250.38: 30.0, 1248.55: 30.0,
                 1378.17: 15.0, 1619.62: 75.0, 1618.03: 75.0, 2130.59: 50.0,
                 2258.43: 75.0}

#: L1B detector arrays, in the order they are concatenated before sorting.
ARMS = ("blue", "red", "SWIR")

#: ``l2_flags`` bits worth surfacing as named masks. OBPG assigns bit i to the
#: i-th name in the variable's own ``flag_meanings``.
FLAGS = ("ATMFAIL", "LAND", "HIGLINT", "HILT", "HISATZEN", "COASTZ",
         "STRAYLIGHT", "CLDICE", "TURBIDW", "HISOLZEN", "NAVFAIL", "CLDSHDSTL")

#: Per-pixel geometry in the L1B ``geolocation_data`` group -> our names.
GEOM = {"solar_zenith": "sza", "solar_azimuth": "saa",
        "sensor_zenith": "vza", "sensor_azimuth": "vaa",
        "height": "elev", "watermask": "water"}

_GRANULE = re.compile(r"^PACE_OCI\.(?P<stamp>\d{8}T\d{6})\.(?P<level>L1B|L2)\."
                      r"(?P<rest>.+)\.nc$", re.IGNORECASE)


def open_pace(
    path: str | Path,
    wl_range: tuple[float, float] | None = None,
    flags: bool = True,
    geometry: bool = True,
    latlon: bool = True,
) -> xr.Dataset:
    """Open a PACE OCI granule.

    Args:
        path: ``PACE_OCI.*.L2.SFREFL.*.nc`` or ``PACE_OCI.*.L1B.*.nc``.
        wl_range: ``(min_nm, max_nm)`` band subset. L2 covers 346-2258 nm in
            122 bands; L1B covers 315-2258 nm in 291.
        flags: decode ``l2_flags`` into named boolean masks (L2 only).
        geometry: attach angles. L2 always gets its own ``csol_z`` (per-scan-line
            centre solar zenith) and ``tilt``; full per-pixel ``sza``, ``saa``,
            ``vza``, ``vaa`` need the L1B sibling and are used when it is found.
            Azimuths
            are converted from OCI's -180..180 convention to 0..360 so they
            match every other reader here. Present
            in L1B; for L2 the matching L1B granule is used if it sits alongside.
        latlon: attach the ``lat``/``lon`` arrays. These are the only
            georeferencing a PACE granule has, so they are needed for
            :func:`hyperproc.georeference`.

    Returns:
        Dataset with ``reflectance`` on ``(y, x, wavelength)``. No CRS - both
        levels are swaths.
    """
    path = Path(path)
    m = _GRANULE.match(path.name)
    if m is None:
        raise ValueError(f"{path.name} is not a PACE OCI granule "
                         f"(expected PACE_OCI.<stamp>.<L1B|L2>.*.nc)")
    level = m.group("level").upper()

    root = xr.open_dataset(path)
    if level == "L2":
        data, wl, fwhm, bidx, long_name = _read_l2(path)
    else:
        data, wl, fwhm, bidx, long_name = _read_l1b(path)

    if wl_range is not None:
        keep = (wl >= wl_range[0]) & (wl <= wl_range[1])
        if not keep.any():
            raise ValueError(f"no PACE bands in {wl_range[0]}-{wl_range[1]} nm "
                             f"(this granule covers {wl.min():.0f}-{wl.max():.0f} nm)")
        data, wl, fwhm, bidx = data.isel(wavelength=keep), wl[keep], fwhm[keep], bidx[keep]

    ds = xr.Dataset(
        {"reflectance": data},
        coords={"wavelength": ("wavelength", wl), "fwhm": ("wavelength", fwhm)},
        attrs={
            "sensor": "PACE", "instrument": root.attrs.get("instrument", "OCI"),
            "level": level, "granule": path.stem,
            "units": "1", "orthorectified": 0,
            "datetime": root.attrs.get("time_coverage_start", ""),
            "spatial_resolution": root.attrs.get("spatialResolution", ""),
            "processing_version": root.attrs.get("processing_version", ""),
        },
    )
    ds["wavelength"].attrs.update(units="nm", long_name="band centre")
    ds["fwhm"].attrs.update(units="nm", long_name="band width",
                            note="nominal 5 nm below 900 nm; real SWIR_bandpass above")
    ds["reflectance"].attrs.update(units="1", long_name=long_name)

    if latlon:
        _add_latlon(ds, path, level)
    if flags and level == "L2":
        _add_flags(ds, path)
    if geometry:
        _add_geometry(ds, path, level, m.group("stamp"))
    finish_bands(ds, index=bidx, fill_value=FILL)
    normalise_angles(ds)
    return ds


# ------------------------------------------------------------------ cubes


def _fwhm_for(wl: np.ndarray) -> np.ndarray:
    """Nominal 5 nm below 900 nm; the real SWIR bandpass above it."""
    out = np.full(wl.size, NOMINAL_FWHM_NM, dtype="float64")
    sw = np.array(sorted(SWIR_BANDPASS))
    for i, w in enumerate(wl):
        if w >= 900.0:
            out[i] = SWIR_BANDPASS[float(sw[np.argmin(np.abs(sw - w))])]
    return out


def _read_l2(path: Path):
    g = xr.open_dataset(path, group="geophysical_data")
    b = xr.open_dataset(path, group="sensor_band_parameters")
    a = g["rhos"]                                   # (line, pixel, wavelength_3d), lazily indexed
    a = a.drop_vars(list(a.coords), errors="ignore").rename(
        {a.dims[0]: "y", a.dims[1]: "x", a.dims[2]: "wavelength"})
    a = a.chunk({"y": 256, "x": -1, "wavelength": -1}).astype("float32")
    a = a.where(a != FILL)
    wl = b["wavelength_3d"].values.astype("float64")
    return a, wl, _fwhm_for(wl), np.arange(wl.size), "surface reflectance"


def _read_l1b(path: Path):
    """Merge the three detector arrays. Each is (band, scan, pixel)."""
    o = xr.open_dataset(path, group="observation_data")
    b = xr.open_dataset(path, group="sensor_band_parameters")
    parts, waves, fwhms = [], [], []
    for arm in ARMS:
        v = o[f"rhot_{arm}"]                          # (band, scan, pixel), lazily indexed
        v = v.drop_vars(list(v.coords), errors="ignore").rename(
            {v.dims[0]: "wavelength", v.dims[1]: "y", v.dims[2]: "x"})
        v = v.chunk({"wavelength": -1, "y": 256, "x": -1}).astype("float32")
        parts.append(v.transpose("y", "x", "wavelength"))
        w = b[f"{arm}_wavelength"].values.astype("float64")
        waves.append(w)
        # SWIR ships a real bandpass; blue/red do not, so use the nominal.
        fwhms.append(b["SWIR_bandpass"].values.astype("float64") if arm == "SWIR"
                     else np.full(w.size, NOMINAL_FWHM_NM))
    data = xr.concat(parts, dim="wavelength")
    wl = np.concatenate(waves)
    fw = np.concatenate(fwhms)
    data = data.where(data != FILL)
    order = np.argsort(wl)                          # blue/red overlap ~5 nm
    return data.isel(wavelength=order), wl[order], fw[order], np.arange(wl.size)[order], "top-of-atmosphere reflectance"


# --------------------------------------------------------------- ancillary


def _add_latlon(ds: xr.Dataset, path: Path, level: str) -> None:
    grp = "navigation_data" if level == "L2" else "geolocation_data"
    g = xr.open_dataset(path, group=grp)
    for name, field in (("lat", "latitude"), ("lon", "longitude")):
        ds[name] = (("y", "x"), g[field].values.astype("float32"))
        ds[name].attrs["units"] = "degrees_north" if name == "lat" else "degrees_east"


def _add_flags(ds: xr.Dataset, path: Path) -> None:
    g = xr.open_dataset(path, group="geophysical_data")
    if "l2_flags" not in g:
        return
    v = g["l2_flags"]
    names = str(v.attrs.get("flag_meanings", "")).split()
    raw = v.values.astype("int64")
    ds["l2_flags"] = (("y", "x"), raw)
    for i, n in enumerate(names):
        if n in FLAGS:
            ds[n.lower()] = (("y", "x"), (raw & (1 << i)) > 0)
            ds[n.lower()].attrs["long_name"] = f"{n} flag (bit {i})"
    if "cldice" in ds:
        ds["cloud"] = ds["cldice"]
        ds["cloud"].attrs["long_name"] = "cloud or ice (CLDICE)"


def _add_scanline(ds: xr.Dataset, path: Path) -> None:
    """Geometry the L2 granule carries itself, so it is usable standalone.

    ``csol_z`` is a per-scan-line *centre* solar zenith and ``tilt`` the OCI
    tilt used to dodge sunglint. Both vary only along track, so they are
    broadcast across it - approximate off-centre, but far better than nothing
    when no L1B sibling is present.
    """
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    try:
        sla = xr.open_dataset(path, group="scan_line_attributes")
        nav = xr.open_dataset(path, group="navigation_data")
    except (OSError, KeyError):
        return
    if "csol_z" in sla and sla["csol_z"].shape == (ny,):
        a = np.broadcast_to(sla["csol_z"].values.astype("float32")[:, None], (ny, nx))
        ds["csol_z"] = (("y", "x"), np.ascontiguousarray(a))
        ds["csol_z"].attrs.update(units="degrees",
                                  long_name="centre solar zenith, per scan line")
    if "tilt" in nav and nav["tilt"].shape == (ny,):
        a = np.broadcast_to(nav["tilt"].values.astype("float32")[:, None], (ny, nx))
        ds["tilt"] = (("y", "x"), np.ascontiguousarray(a))
        ds["tilt"].attrs.update(units="degrees",
                                long_name="OCI tilt angle (sunglint avoidance)")
    if "time" in sla and sla["time"].shape == (ny,):
        ds.coords["scan_time"] = ("y", sla["time"].values)
        ds["scan_time"].attrs["long_name"] = "scan line time, seconds since 1970-01-01"


def _add_geometry(ds: xr.Dataset, path: Path, level: str, stamp: str) -> None:
    """Full per-pixel angles from L1B; L2 also keeps its own scan-line values."""
    src = path
    if level == "L2":
        _add_scanline(ds, path)
        cand = sorted(path.parent.glob(f"PACE_OCI.{stamp}.L1B.*.nc"))
        if not cand:
            # Standalone L2: csol_z is the only solar zenith available.
            if "csol_z" in ds:
                ds["sza"] = ds["csol_z"]
                ds["sza"].attrs["long_name"] = (
                    "solar zenith from csol_z (per scan line; no L1B sibling found)")
            ds.attrs["geometry_source"] = "L2 scan_line_attributes only"
            return
        src = cand[0]
    try:
        g = xr.open_dataset(src, group="geolocation_data")
    except (OSError, KeyError) as exc:
        ds.attrs["geometry_source"] = "none"
        warnings.warn(f"{src.name}: geolocation_data group could not be read ({type(exc).__name__}); "
                      "geometry layers not attached")
        return
    for field, name in GEOM.items():
        if field not in g:
            continue
        a = g[field].values
        if a.shape != (ds.sizes["y"], ds.sizes["x"]):
            continue
        if name == "water":
            ds[name] = (("y", "x"), a.astype(bool))
            continue
        a = a.astype("float32")
        if name in ("saa", "vaa"):
            # OCI stores azimuth as -180..180; every other reader in this
            # package reports 0..360, so harmonise rather than pass it through.
            a = np.mod(a, 360.0)
        ds[name] = (("y", "x"), a)
        if name in ("sza", "saa", "vza", "vaa"):
            ds[name].attrs["units"] = "degrees"
    if "elev" in ds:
        ds["elev"].attrs["units"] = "m"
    if "vaa" in ds and "saa" in ds:
        # Not stored by OCI; derived as (VAA - SAA) mod 360, matching the
        # relative azimuth PRISMA ships directly. This is the angle BRDF
        # kernels actually take.
        ds["raa"] = (("y", "x"),
                     np.mod(ds["vaa"].values - ds["saa"].values, 360.0).astype("float32"))
        ds["raa"].attrs.update(units="degrees",
                               long_name="relative azimuth (VAA - SAA, mod 360)")
    ds.attrs["geometry_source"] = src.name
