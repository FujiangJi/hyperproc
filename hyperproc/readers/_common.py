"""Helpers shared by the readers."""
from __future__ import annotations


def crs_text(crs) -> str | None:
    """One spelling for ``attrs["crs"]``: ``"EPSG:<code>"`` when the CRS has an
    EPSG code, WKT otherwise, ``None`` when there is no CRS at all.

    Readers get their CRS from very different places (rasterio objects, ENVI
    map info, netCDF ``spatial_ref`` WKT, integer EPSG attributes). Writing them
    all through this keeps the attribute comparable across sensors and stops
    ``str(None)`` from turning into the literal text ``"None"``, which the
    GeoTIFF writer would then try to use as a projection.
    """
    if crs is None:
        return None
    text = str(crs).strip()
    if not text or text.lower() == "none":
        return None
    try:
        from rasterio.crs import CRS
        c = CRS.from_user_input(crs if not isinstance(crs, str) else text)
    except Exception:
        return text
    epsg = c.to_epsg()
    return f"EPSG:{epsg}" if epsg else c.to_wkt()


import re as _re

import numpy as np
import xarray as xr

#: Water-vapour absorption windows (nm) no imaging spectrometer sees through.
#: Used for ``good_wavelength`` when the provider ships no per-band flag.
WATER_WINDOWS = ((1350.0, 1440.0), (1800.0, 1960.0))

_ID_PATTERNS = (
    _re.compile(r"(?:AV[35]|ang)(\d{4})(\d{2})(\d{2})t(\d{2})(\d{2})(\d{2})"),   # AVIRIS-3/5, NG
    _re.compile(r"^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})_"),             # Tanager strip id
)
_CLASSIC = _re.compile(r"^f(\d{2})(\d{2})(\d{2})t\d{2}")


def datetime_from_id(granule: str) -> str | None:
    """ISO acquisition time encoded in a granule id, or None.

    ``AV320231005t181518`` -> ``2023-10-05T18:15:18``; ``ang20220224t210144``
    likewise; Tanager ``20250503_064345_16_4001`` -> ``2025-05-03T06:43:45``;
    AVIRIS Classic ``f201013t01p00r10`` carries the date only.
    """
    for pat in _ID_PATTERNS:
        m = pat.search(granule)
        if m:
            y, mo, d, hh, mm, ss = m.groups()
            return f"{y}-{mo}-{d}T{hh}:{mm}:{ss}"
    m = _CLASSIC.match(granule)
    if m:
        yy, mo, d = m.groups()
        return f"20{yy}-{mo}-{d}"
    return None


def finish_bands(ds: xr.Dataset, *, index=None, good=None, good_source: str | None = None,
                 fill_value=None, stem: str | None = None, datetime: str | None = None) -> None:
    """Complete the band/attribute contract every reader promises.

    Sets what is still missing: ``band_index`` (0-based position of each band
    in the source file - ``index`` after any subsetting, else 0..n-1),
    ``good_wavelength`` (``good`` from the provider, else the package's
    water-window default), ``fill_value`` (the source no-data value),
    ``stem`` (defaults to ``granule``) and ``datetime``. Never overwrites a
    value a reader already set, so calling it is always safe.
    """
    n = ds.sizes["wavelength"]
    if "band_index" not in ds.coords:
        idx = np.arange(n) if index is None else np.asarray(index, dtype=int)
        ds.coords["band_index"] = ("wavelength", idx)
        ds["band_index"].attrs["long_name"] = "0-based band position in the source file"
    if "good_wavelength" not in ds.coords:
        if good is None:
            wl = np.asarray(ds["wavelength"].values, dtype=float)
            good = np.ones(n, dtype=bool)
            for lo, hi in WATER_WINDOWS:
                good &= ~((wl >= lo) & (wl <= hi))
            good_source = good_source or "package default: water-vapour windows 1350-1440 and 1800-1960 nm"
        ds.coords["good_wavelength"] = ("wavelength", np.asarray(good, dtype=bool))
        ds["good_wavelength"].attrs["long_name"] = f"usable band ({good_source or 'provider flag'})"
        ds.attrs.setdefault("good_bands_source", good_source or "provider flag")
    if fill_value is not None and "fill_value" not in ds.attrs:
        ds.attrs["fill_value"] = fill_value
    if "stem" not in ds.attrs:
        ds.attrs["stem"] = stem or ds.attrs.get("granule")
    if datetime and not ds.attrs.get("datetime"):
        ds.attrs["datetime"] = datetime


_SCALAR_ALIASES = {
    "sza": ("sun_zenith", "sza_center", "solar_zenith"),
    "saa": ("sun_azimuth", "saa_center", "solar_azimuth"),
    "vza": ("view_zenith", "vza_center", "sceneIncidenceAngle"),
    "vaa": ("view_azimuth", "vaa_center"),
}


def normalise_angles(ds: xr.Dataset) -> None:
    """One angle convention for every reader.

    * scene-level scalars become attrs ``sza``/``saa``/``vza``/``vaa``
      (the provider's names are kept as well);
    * a scalar with no matching layer is broadcast lazily to a constant
      ``(y, x)`` layer, so geometry export and ``describe`` treat every sensor
      alike (``long_name`` says it is scene-level);
    * azimuths and aspect are wrapped to [0, 360);
    * ``raa`` = (vaa - saa) mod 360 is added when both azimuth layers exist.
    """
    import dask.array as dsk

    for std, aliases in _SCALAR_ALIASES.items():
        if std not in ds.attrs:
            for a in aliases:
                v = ds.attrs.get(a)
                if isinstance(v, (int, float)) and np.isfinite(v):
                    ds.attrs[std] = float(v)
                    break
    for name in ("saa", "vaa", "aspect", "raa"):
        if name in ds and ds[name].ndim == 2:
            da = ds[name]
            ds[name] = (da.dims, np.mod(da.data, 360.0)) if hasattr(da.data, "dask") else (da.dims, np.mod(da.values, 360.0))
            ds[name].attrs.update(da.attrs)
    if "y" in ds.dims and "x" in ds.dims:
        shape = (ds.sizes["y"], ds.sizes["x"])
        for name in ("sza", "saa", "vza", "vaa"):
            v = ds.attrs.get(name)
            if name not in ds and isinstance(v, float) and np.isfinite(v):
                ds[name] = (("y", "x"), dsk.full(shape, np.float32(v), dtype="float32", chunks=(min(1024, shape[0]), -1)))
                ds[name].attrs.update(units="degrees", long_name=f"{name} (scene-level constant from the provider metadata)")
    if "raa" not in ds and "vaa" in ds and "saa" in ds:
        raa = np.mod(ds["vaa"] - ds["saa"], 360.0).astype("float32")
        ds["raa"] = raa
        ds["raa"].attrs.update(units="degrees", long_name="relative azimuth (VAA - SAA, mod 360)")
