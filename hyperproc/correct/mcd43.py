"""MODIS MCD43A1 BRDF model parameters, the input to satellite BRDF normalisation.

MCD43A1 is a daily product: for every 500 m cell it gives the three weights of
the RossThick-LiSparseReciprocal model (``iso``, ``vol``, ``geo``) for MODIS
bands 1-7, fitted to all cloud-free observations in a 16-day window centred on
the date. Those weights describe the shape of the surface reflectance as a
function of Sun and view angle, which is exactly what a single hyperspectral
scene cannot know about itself.

    from hyperproc.correct import mcd43
    p = mcd43.fetch(bounds=(-121.0, 34.0, -119.8, 35.1), date="2023-04-22",
                    out_dir="cache/mcd43")
    par = p.sample(lon, lat)          # (..., 7 MODIS bands, 3 kernels)

Sources
-------
``source="gee"``
    Google Earth Engine, collection ``MODIS/061/MCD43A1`` (plus ``MCD43A2``
    for the per-band quality and snow flags). Needs ``earthengine-api`` and a
    one-off ``earthengine authenticate``; recent versions also need a Cloud
    project (``project=`` or ``$EARTHENGINE_PROJECT``). Downloaded in tiles
    through ``getDownloadURL`` so no other client library is required.
``source="local"``
    A GeoTIFF written by an earlier ``fetch``, or any 21-band stack whose band
    descriptions are the MCD43A1 parameter names.

Resolution
----------
MCD43A1 is a 500 m product, and 1/240 degree (about 464 m) is its native step.
``fetch(res=None)``, the default, adapts to the image: it never asks for a grid
finer than native, because upsampling adds no information that bilinear
sampling at each pixel's own coordinates does not already give, and it asks for
a coarser grid when the image pixels are coarser, so that MODIS cells are
**averaged** over the footprint instead of point-sampled. PACE OCI is the case
that needs this: its 1.2 km pixels each cover about six MODIS cells, and a
bilinear sample of the four nearest ones would alias. The coarse grids stay
whole multiples of the native step, so an aggregation always covers whole
MODIS cells. :func:`resolution_of` reports what a dataset asks for.

The download is cached: the same bounds, date and resolution give the same
file name under ``$HYPERPROC_CACHE_DIR/mcd43`` (or ``out_dir``), and an
existing file is reused unless ``overwrite=True``.

Fill values
-----------
Earth Engine delivers masked cells as zero, and zero is a legal parameter
value, so the image is unmasked to the product's own fill (32767) before the
download and only that value counts as "no data". Valid parameters are scaled
by 0.001 into reflectance units.
"""
from __future__ import annotations

import io
import os
import time
import warnings
from dataclasses import dataclass, field
from datetime import date as _date, datetime, timedelta
from pathlib import Path

import numpy as np

__all__ = ["MODIS_BANDS", "MODIS_RANGES", "MODIS_CENTRES", "KERNELS", "PARAM_BANDS",
           "Params", "cache_dir", "fetch", "read", "grid_for", "bounds_of", "date_of",
           "resolution_of", "step_for", "available"]

# Nominal spectral coverage of the seven MODIS land bands (nm), as used to map
# an instrument's wavelengths onto the seven parameter sets.
MODIS_RANGES = {1: (620.0, 670.0), 2: (841.0, 876.0), 3: (459.0, 479.0), 4: (545.0, 565.0),
                5: (1230.0, 1250.0), 6: (1628.0, 1652.0), 7: (2105.0, 2155.0)}
MODIS_BANDS = tuple(sorted(MODIS_RANGES))
MODIS_CENTRES = {b: 0.5 * (lo + hi) for b, (lo, hi) in MODIS_RANGES.items()}
KERNELS = ("iso", "vol", "geo")

PARAM_BANDS = [f"BRDF_Albedo_Parameters_Band{b}_{k}" for b in MODIS_BANDS for k in KERNELS]
# MCD43A2 v061 names the per-band flag BRDF_Albedo_Band_Quality_BandN (the
# "Mandatory_Quality" name belonged to v006). Values: 0 best full inversion,
# 1 full inversion, 2 magnitude inversion (>= 7 looks), 3 magnitude inversion
# (2-6 looks), 255 fill. Snow_BRDF_Albedo: 0 snow-free, 1 snow, 255 fill.
QA_BANDS = [f"BRDF_Albedo_Band_Quality_Band{b}" for b in MODIS_BANDS] + ["Snow_BRDF_Albedo"]

COLLECTION = "MODIS/061/MCD43A1"
QA_COLLECTION = "MODIS/061/MCD43A2"
SCALE = 0.001
FILL = 32767
QA_FILL = 255
RES_DEG = 1.0 / 240.0          # 0.00416667 deg, the 500 m MODIS step in geographic coordinates
TILE = 512                     # download block (px); 512 x 512 x 21 int16 is ~11 MB


def cache_dir() -> Path:
    d = Path(os.environ.get("HYPERPROC_CACHE_DIR", "~/.cache/hyperproc")).expanduser() / "mcd43"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
# the parameter stack                                                          #
# --------------------------------------------------------------------------- #

@dataclass
class Params:
    """A window of MCD43A1 parameters on a geographic grid.

    Attributes:
        values: ``(ny, nx, 7, 3)`` float32 in reflectance units, NaN where the
            product has no retrieval. The last axis is ``iso, vol, geo``.
        transform: affine of the grid, ``(a, b, c, d, e, f)`` as
            ``x = c + a*col``, ``y = f + e*row`` (pixel corners).
        crs: always ``"EPSG:4326"`` for a downloaded stack.
        date: the acquisition date actually used, ``YYYY-MM-DD``.
        quality: ``(ny, nx, 7)`` uint8 band quality (0 best full inversion,
            1 full inversion, 2-3 magnitude inversion, 255 fill) or None.
        snow: ``(ny, nx)`` uint8 snow flag (0 snow-free, 1 snow, 255 fill) or None.
    """

    values: np.ndarray
    transform: tuple
    crs: str = "EPSG:4326"
    date: str = ""
    quality: np.ndarray | None = None
    snow: np.ndarray | None = None
    path: Path | None = None
    attrs: dict = field(default_factory=dict)

    @property
    def shape(self) -> tuple:
        return self.values.shape[:2]

    def coverage(self) -> float:
        """Fraction of cells with a retrieval in every band (iso term, band 1)."""
        return float(np.isfinite(self.values[..., 0, 0]).mean())

    def masked(self, qa_max: int | None = 3, snow: bool = True) -> "Params":
        """A copy with low-quality and (optionally) snow-covered cells set to NaN.

        Args:
            qa_max: keep cells whose band quality is <= this. The default 3
                keeps every retrieval, including magnitude inversions. That is
                deliberate: a magnitude inversion scales an archetype shape to
                the observed brightness, and a common factor on all three
                weights cancels in the c-factor ratio, so it costs far less
                here than it would in an albedo. Dropping them instead leaves
                holes that make neighbouring pixels inconsistent. Pass 1 for
                full inversions only; None keeps every cell including fill.
            snow: drop cells flagged as snow-covered. A snow BRDF is a real
                measurement, but the surface it describes is usually gone by
                the time a different sensor sees it.
        """
        out = np.array(self.values, copy=True)
        if qa_max is not None and self.quality is not None:
            bad = (self.quality > qa_max) | (self.quality == QA_FILL)
            out[bad] = np.nan                      # (ny, nx, 7) broadcasts over the kernel axis
        if snow and self.snow is not None:
            out[self.snow == 1] = np.nan
        return Params(out, self.transform, self.crs, self.date, self.quality, self.snow,
                      self.path, dict(self.attrs, masked=f"qa<={qa_max} snow={snow}"))

    def rowcol(self, lon, lat) -> tuple:
        """Fractional row/column of lon/lat in this grid, cell centres at .0."""
        a, _, c, _, e, f = self.transform
        return (np.asarray(lat, dtype="float64") - f) / e - 0.5, (np.asarray(lon, dtype="float64") - c) / a - 0.5

    def sample(self, lon, lat, method: str = "bilinear") -> np.ndarray:
        """Parameters at scattered points, shape ``lon.shape + (7, 3)``.

        Sampling the parameters (rather than warping them to the image grid and
        reading back) keeps one code path for projected images and for swaths,
        where every pixel has its own longitude and latitude.

        NaN cells are skipped and the remaining bilinear weights renormalised,
        so a point next to a gap still gets a value; a point whose four
        neighbours are all fill comes back NaN.
        """
        lon = np.asarray(lon, dtype="float64")
        lat = np.asarray(lat, dtype="float64")
        shape = lon.shape
        r, c = self.rowcol(lon.ravel(), lat.ravel())
        ny, nx = self.shape
        vals = self.values.reshape(ny, nx, -1)
        nlayer = vals.shape[-1]
        out = np.full((r.size, nlayer), np.nan, dtype="float32")

        if method == "nearest":
            r0 = np.rint(r).astype("int64"); c0 = np.rint(c).astype("int64")
            ok = (r0 >= 0) & (r0 < ny) & (c0 >= 0) & (c0 < nx) & np.isfinite(r) & np.isfinite(c)
            if ok.any():
                out[ok] = vals[r0[ok], c0[ok]]
            return out.reshape(shape + (len(MODIS_BANDS), len(KERNELS)))
        if method != "bilinear":
            raise ValueError(f"method must be 'bilinear' or 'nearest'; got {method!r}")

        r = np.where(np.isfinite(r), r, -1e9)
        c = np.where(np.isfinite(c), c, -1e9)
        r0 = np.floor(r).astype("int64"); c0 = np.floor(c).astype("int64")
        fr = (r - r0).astype("float32"); fc = (c - c0).astype("float32")
        neigh = ((r0, c0, (1 - fr) * (1 - fc)), (r0, c0 + 1, (1 - fr) * fc),
                 (r0 + 1, c0, fr * (1 - fc)), (r0 + 1, c0 + 1, fr * fc))
        idx, wts = [], []
        for rr, cc, w in neigh:
            inside = (rr >= 0) & (rr < ny) & (cc >= 0) & (cc < nx)
            idx.append(np.where(inside, np.clip(rr, 0, ny - 1) * nx + np.clip(cc, 0, nx - 1), 0))
            wts.append(np.where(inside, w, 0.0).astype("float32"))
        flat = vals.reshape(ny * nx, nlayer)
        for k in range(nlayer):                       # one layer at a time keeps the gathers small
            layer = flat[:, k]
            acc = np.zeros(r.size, dtype="float32")
            wsum = np.zeros(r.size, dtype="float32")
            for i, w in zip(idx, wts):
                v = layer[i]
                good = np.isfinite(v) & (w > 0)
                acc += np.where(good, v * w, 0.0)
                wsum += np.where(good, w, 0.0)
            out[:, k] = np.where(wsum > 0, acc / np.where(wsum > 0, wsum, 1.0), np.nan)
        return out.reshape(shape + (len(MODIS_BANDS), len(KERNELS)))

    def to_geotiff(self, path) -> Path:
        """Write the stack back out (21 parameter bands, then quality and snow)."""
        import rasterio
        from rasterio.transform import Affine
        ny, nx = self.shape
        layers = [self.values[..., b, k] / SCALE for b in range(len(MODIS_BANDS)) for k in range(len(KERNELS))]
        arr = np.where(np.isfinite(layers), np.nan_to_num(layers, nan=FILL), FILL)
        names = list(PARAM_BANDS)
        if self.quality is not None:
            arr = np.concatenate([arr, np.moveaxis(self.quality, -1, 0)], axis=0)
            names += QA_BANDS[:len(MODIS_BANDS)]
        if self.snow is not None:
            arr = np.concatenate([arr, self.snow[None]], axis=0)
            names += ["Snow_BRDF_Albedo"]
        a, b, c, d, e, f = self.transform
        path = Path(path)
        with rasterio.open(path, "w", driver="GTiff", height=ny, width=nx, count=arr.shape[0],
                           dtype="int16", crs=self.crs, transform=Affine(a, b, c, d, e, f),
                           nodata=FILL, compress="deflate", tiled=True) as dst:
            dst.write(np.rint(arr).astype("int16"))
            for i, n in enumerate(names, start=1):
                dst.set_band_description(i, n)
            tags = {"date": self.date, "collection": COLLECTION,
                    "scale_factor": str(SCALE), "fill_value": str(FILL)}
            tags.update({k: str(v) for k, v in self.attrs.items()})   # attrs may repeat a key
            dst.update_tags(**tags)
        return path


def read(path) -> Params:
    """Read a parameter stack written by :meth:`Params.to_geotiff` (or an equivalent)."""
    import rasterio
    path = Path(path)
    with rasterio.open(path) as src:
        names = [d or f"band_{i}" for i, d in enumerate(src.descriptions, start=1)]
        data = src.read()
        tags = src.tags()
        transform = tuple(src.transform)[:6]
        crs = str(src.crs) if src.crs else "EPSG:4326"
    index = {n: i for i, n in enumerate(names)}
    missing = [n for n in PARAM_BANDS if n not in index]
    if missing:
        raise ValueError(f"{path.name} is missing {len(missing)} parameter bands, first {missing[0]!r}; "
                         "band descriptions must be the MCD43A1 parameter names")
    ny, nx = data.shape[1:]
    vals = np.full((ny, nx, len(MODIS_BANDS), len(KERNELS)), np.nan, dtype="float32")
    for bi, b in enumerate(MODIS_BANDS):
        for ki, k in enumerate(KERNELS):
            layer = data[index[f"BRDF_Albedo_Parameters_Band{b}_{k}"]].astype("float32")
            layer[(layer == FILL) | (layer <= -FILL)] = np.nan
            vals[..., bi, ki] = layer * SCALE
    qa = None
    if all(n in index for n in QA_BANDS[:len(MODIS_BANDS)]):
        qa = np.stack([data[index[n]] for n in QA_BANDS[:len(MODIS_BANDS)]], axis=-1).astype("uint8")
    snow = data[index["Snow_BRDF_Albedo"]].astype("uint8") if "Snow_BRDF_Albedo" in index else None
    return Params(vals, transform, crs, tags.get("date", ""), qa, snow, path, tags)


# --------------------------------------------------------------------------- #
# what to ask for: the scene's footprint and date                              #
# --------------------------------------------------------------------------- #

def bounds_of(ds) -> tuple:
    """Geographic bounds ``(w, s, e, n)`` of a hyperproc dataset, in degrees.

    Uses the per-pixel ``lon``/``lat`` layers when the dataset has them (swath
    grids), otherwise the map grid, reprojected to EPSG:4326 if needed.
    """
    if "lon" in ds and "lat" in ds:
        lon = np.asarray(ds["lon"].values, dtype="float64"); lat = np.asarray(ds["lat"].values, dtype="float64")
        ok = np.isfinite(lon) & np.isfinite(lat) & (np.abs(lon) <= 180) & (np.abs(lat) <= 90)
        if not ok.any():
            raise ValueError("lon/lat layers hold no valid values")
        return (float(lon[ok].min()), float(lat[ok].min()), float(lon[ok].max()), float(lat[ok].max()))
    if "x" not in ds.coords or "y" not in ds.coords:
        raise ValueError("dataset has neither lon/lat layers nor x/y coordinates; cannot locate it")
    x = np.asarray(ds["x"].values, dtype="float64"); y = np.asarray(ds["y"].values, dtype="float64")
    w, s, e, n = x.min(), y.min(), x.max(), y.max()
    crs = str(ds.attrs.get("crs", "") or "")
    if crs and crs.upper() not in ("EPSG:4326", "OGC:CRS84"):
        from pyproj import Transformer
        tr = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        xs, ys = np.meshgrid([w, e], [s, n])
        lon, lat = tr.transform(xs.ravel(), ys.ravel())
        return (float(np.min(lon)), float(np.min(lat)), float(np.max(lon)), float(np.max(lat)))
    return (float(w), float(s), float(e), float(n))


def date_of(source) -> str:
    """The acquisition date as ``YYYY-MM-DD``.

    Args:
        source: an open dataset, or a granule path or file name. A dataset's
            ``datetime`` attribute wins; otherwise the first eight-digit date
            in the granule name is used, which every sensor in the package
            puts there.

    Raises:
        ValueError: nothing in the name or the attributes looks like a date.
    """
    if isinstance(source, (str, Path)):
        stamp, name = "", Path(str(source)).name
    else:
        stamp = str(source.attrs.get("datetime", "") or "")
        name = str(source.attrs.get("granule", "") or source.attrs.get("stem", "") or "")
    if stamp:
        for cut in (19, 10):
            try:
                return datetime.fromisoformat(stamp[:cut].replace("Z", "")).date().isoformat()
            except ValueError:
                continue
    for i in range(len(name) - 7):
        chunk = name[i:i + 8]
        if chunk.isdigit() and "1900" < chunk[:4] < "2100":
            try:
                return _date(int(chunk[:4]), int(chunk[4:6]), int(chunk[6:8])).isoformat()
            except ValueError:
                continue
    raise ValueError(f"no acquisition date in {name or 'the dataset attributes'!r}; pass date= explicitly")


def available(date: str, days: int = 0, collection: str = COLLECTION, project: str | None = None) -> str:
    """The date of the nearest MCD43A1 image within ``days`` of ``date``.

    A one-call connectivity and coverage check: it proves Earth Engine is
    reachable and that the scene's own date has a granule, without downloading
    anything.

    Raises:
        RuntimeError: no image in the window (or Earth Engine is unreachable).
    """
    ee = _init_ee(project)
    return _ee_image(ee, collection, PARAM_BANDS[:1], date, days)[1]


def resolution_of(ds) -> float:
    """The dataset's ground sample distance, in degrees.

    Read from the map grid's own coordinates where there is one (converted
    from metres for a projected CRS), otherwise from the spacing of the
    per-pixel ``lon``/``lat`` layers of a swath. The larger of the two axes
    wins, so the answer is never finer than the image really is.
    """
    if "x" in ds.coords and "y" in ds.coords and ds.sizes.get("x", 0) > 1 and ds.sizes.get("y", 0) > 1:
        dx = float(np.median(np.abs(np.diff(np.asarray(ds["x"].values, dtype="float64")))))
        dy = float(np.median(np.abs(np.diff(np.asarray(ds["y"].values, dtype="float64")))))
        step = max(dx, dy)
        crs = str(ds.attrs.get("crs", "") or "")
        if crs and crs.upper() not in ("EPSG:4326", "OGC:CRS84"):
            step /= 111320.0                       # projected CRS: metres -> degrees, nominal
        return step
    if "lon" in ds and "lat" in ds:
        lon = np.asarray(ds["lon"].values, dtype="float64")
        lat = np.asarray(ds["lat"].values, dtype="float64")
        if lon.ndim == 2:
            # A swath grid is rotated with respect to north, so the step along a row is not
            # the change in longitude alone: both components count, and longitude shrinks
            # by cos(latitude). Taking one axis at a time would underestimate the pixel.
            cos_lat = np.cos(np.radians(np.clip(lat, -89.9, 89.9)))
            steps = []
            if lon.shape[1] > 1:
                steps.append(np.nanmedian(np.hypot(np.diff(lon, axis=1) * cos_lat[:, :-1],
                                                   np.diff(lat, axis=1))))
            if lon.shape[0] > 1:
                steps.append(np.nanmedian(np.hypot(np.diff(lon, axis=0) * cos_lat[:-1, :],
                                                   np.diff(lat, axis=0))))
            steps = [s for s in steps if np.isfinite(s) and s > 0]
            if steps:
                return float(max(steps))
    raise ValueError("cannot measure the dataset's resolution: it has neither x/y coordinates "
                     "nor lon/lat layers; pass res= explicitly")


def step_for(ds=None, res: float | None = None) -> tuple:
    """Resolve the MODIS grid step to use, as ``(res, k)``.

    ``k`` is how many native MODIS cells go into one output cell, so ``k = 1``
    means the product's own grid and ``k > 1`` means an aggregation.
    """
    if res is not None:
        return float(res), max(1, int(round(float(res) / RES_DEG)))
    if ds is None:
        return RES_DEG, 1
    try:
        image = resolution_of(ds)
    except ValueError:
        return RES_DEG, 1
    k = max(1, int(np.floor(image / RES_DEG + 1e-9)))    # never finer than native, never coarser than the pixel
    return k * RES_DEG, k


def grid_for(bounds, res: float = RES_DEG, pad: float = 0.05) -> tuple:
    """Snap ``(w, s, e, n)`` outward onto a global ``res``-degree grid.

    Returns ``(transform, nx, ny)``. Snapping means two scenes that overlap ask
    for the same cells, so the cache is shared and there is no half-pixel shift
    between them.
    """
    w, s, e, n = bounds
    pad = max(float(pad), 2.0 * res)            # bilinear sampling needs neighbours at the edge
    x0 = np.floor((w - pad) / res) * res
    x1 = np.ceil((e + pad) / res) * res
    y0 = np.floor((s - pad) / res) * res
    y1 = np.ceil((n + pad) / res) * res
    nx = int(round((x1 - x0) / res)); ny = int(round((y1 - y0) / res))
    return (res, 0.0, float(x0), 0.0, -res, float(y1)), nx, ny


# --------------------------------------------------------------------------- #
# Earth Engine                                                                 #
# --------------------------------------------------------------------------- #

def _init_ee(project: str | None = None):
    try:
        import ee
    except ImportError as exc:                       # pragma: no cover - environment dependent
        raise ImportError(
            "the 'gee' source needs earthengine-api:\n"
            "    pip install 'hyperproc[brdf]'\n"
            "then authenticate once with 'earthengine authenticate' (or "
            "ee.Authenticate()). Recent versions also need a Cloud project: pass "
            "project='my-project' or set $EARTHENGINE_PROJECT."
        ) from exc
    project = project or os.environ.get("EARTHENGINE_PROJECT") or None
    try:
        ee.Initialize(project=project) if project else ee.Initialize()
    except Exception as exc:                          # pragma: no cover - environment dependent
        raise RuntimeError(
            f"Earth Engine would not initialise ({exc}). Run 'earthengine authenticate' once, and "
            "pass project='<cloud project>' (or set $EARTHENGINE_PROJECT) if the account needs one."
        ) from exc
    return ee


def _ee_image(ee, collection: str, bands: list, date: str, days: int):
    """The image for ``date``, or the nearest one within +/- ``days``."""
    d0 = _date.fromisoformat(date)
    offsets = [0]
    for k in range(1, int(days) + 1):
        offsets += [-k, k]
    for off in offsets:
        day = (d0 + timedelta(days=off)).isoformat()
        col = ee.ImageCollection(collection).filterDate(day, (d0 + timedelta(days=off + 1)).isoformat())
        if col.size().getInfo():
            return col.first().select(bands), day
    raise RuntimeError(f"no {collection} image within {days} day(s) of {date}")


def _aggregate(ee, img, k: int, transform: tuple, reducer: str = "mean"):
    """Average ``k x k`` native MODIS cells into one output cell.

    Done on the *masked* image, so cells with no retrieval never contribute to
    the mean; the caller unmasks to the fill value afterwards. Point-sampling a
    500 m field at kilometre spacing would alias instead, which is why this
    exists at all (PACE OCI is the sensor that needs it).
    """
    if k <= 1:
        return img
    res, _, x0, _, _, y1 = transform
    red = ee.Reducer.mean() if reducer == "mean" else ee.Reducer.max()
    return (img.reduceResolution(reducer=red, maxPixels=min(10000, max(64, 4 * k * k)), bestEffort=True)
               .reproject(crs="EPSG:4326", crsTransform=[res, 0.0, x0, 0.0, -res, y1]))


def _download(ee, img, bands: list, transform: tuple, nx: int, ny: int, fill: int,
              tile: int = TILE, verbose: bool = True, retries: int = 4) -> np.ndarray:
    """Pull a pinned grid out of Earth Engine, tile by tile, as ``(ny, nx, nband)``."""
    import requests
    res, _, x0, _, _, y1 = transform
    img = img.unmask(fill)                      # masked cells arrive as 0 otherwise, and 0 is a legal value
    out = np.full((ny, nx, len(bands)), float(fill), dtype="float64")
    blocks = [(r, c) for r in range(0, ny, tile) for c in range(0, nx, tile)]
    for i, (r, c) in enumerate(blocks, start=1):
        h = min(tile, ny - r); w = min(tile, nx - c)
        params = {"bands": bands, "format": "NPY", "crs": "EPSG:4326",
                  "crs_transform": [res, 0.0, x0 + c * res, 0.0, -res, y1 - r * res],
                  "dimensions": f"{w}x{h}"}
        for attempt in range(retries):
            try:
                url = img.getDownloadURL(params)
                resp = requests.get(url, timeout=900)
                resp.raise_for_status()
                arr = np.load(io.BytesIO(resp.content), allow_pickle=False)
                break
            except Exception as exc:                  # pragma: no cover - network dependent
                if attempt == retries - 1:
                    raise RuntimeError(f"Earth Engine download failed for block {i}/{len(blocks)}: {exc}") from exc
                time.sleep(2 ** attempt)
        out[r:r + h, c:c + w] = np.stack([arr[b] for b in bands], axis=-1)
        if verbose and (i == len(blocks) or i % 10 == 0):
            print(f"    block {i}/{len(blocks)}", flush=True)
    return out


def fetch(bounds=None, date: str | None = None, out_dir=None, *, ds=None, source: str = "gee",
          res: float | None = None, pad: float = 0.05, days: int = 8, quality: bool = True,
          project: str | None = None, overwrite: bool = False, tile: int = TILE,
          verbose: bool = True) -> Params:
    """MCD43A1 parameters covering ``bounds`` on ``date``, downloaded once and cached.

    Args:
        bounds: ``(w, s, e, n)`` in degrees. Taken from ``ds`` when omitted.
        date: ``YYYY-MM-DD``. Taken from ``ds`` when omitted.
        out_dir: where the GeoTIFF goes; default ``$HYPERPROC_CACHE_DIR/mcd43``.
        ds: a hyperproc dataset to read the footprint and date from.
        source: ``"gee"`` to download, ``"local"`` to only use the cache.
        res: grid step in degrees. The default None adapts to ``ds``: the
            product's native 1/240 degree for any image finer than that, and a
            whole multiple of it, with the MODIS cells averaged, for an image
            coarser than that. Pass a number to pin it.
        pad: degrees added around the footprint so bilinear sampling has
            neighbours at the edge.
        days: how far to look for a granule if the exact date is missing.
        quality: also fetch the MCD43A2 per-band quality and snow flags.
        project: Earth Engine Cloud project.
        overwrite: re-download even if the cached file exists.

    Returns:
        :class:`Params`.
    """
    if ds is not None:
        bounds = bounds or bounds_of(ds)
        date = date or date_of(ds)
    if bounds is None or date is None:
        raise ValueError("pass bounds= and date=, or ds= to take them from a dataset")
    res, k = step_for(ds, res)
    transform, nx, ny = grid_for(bounds, res=res, pad=pad)
    out_dir = Path(out_dir) if out_dir else cache_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (f"MCD43A1_{date}_{transform[2]:.4f}_{transform[5]:.4f}_{nx}x{ny}"
            f"_{1 / res:.2f}cpd.tif")
    path = out_dir / name
    if path.is_file() and not overwrite:
        if verbose:
            print(f"  MCD43A1 [cached] {path.name}")
        return read(path)
    if source == "local":
        raise FileNotFoundError(f"no cached parameter stack at {path}; run with source='gee' to download it")
    if source != "gee":
        raise ValueError(f"source must be 'gee' or 'local'; got {source!r}")

    ee = _init_ee(project)
    img, used = _ee_image(ee, COLLECTION, PARAM_BANDS, date, days)
    if verbose:
        how = "native" if k == 1 else f"{k}x{k} native cells averaged"
        print(f"  MCD43A1 {used} ({'exact date' if used == date else f'nearest within {days} d'}) "
              f"{nx} x {ny} cells at {res * 111320:.0f} m ({how}) -> {path.name}")
    raw = _download(ee, _aggregate(ee, img, k, transform, "mean"), PARAM_BANDS,
                    transform, nx, ny, FILL, tile=tile, verbose=verbose)
    vals = raw.astype("float32").reshape(ny, nx, len(MODIS_BANDS), len(KERNELS))
    vals[(raw.reshape(vals.shape) == FILL) | (raw.reshape(vals.shape) <= -FILL)] = np.nan
    vals *= SCALE

    qa = snow = None
    if quality:
        try:
            qimg, qused = _ee_image(ee, QA_COLLECTION, QA_BANDS, used, 0)
            # flags, not measurements: the worst sub-cell wins, so an aggregated cell is
            # never reported as better quality or more snow-free than its parts
            qraw = _download(ee, _aggregate(ee, qimg, k, transform, "max"), QA_BANDS,
                             transform, nx, ny, QA_FILL, tile=tile, verbose=False)
            qa = np.clip(np.rint(qraw[..., :len(MODIS_BANDS)]), 0, 255).astype("uint8")
            snow = np.clip(np.rint(qraw[..., -1]), 0, 255).astype("uint8")
        except Exception as exc:
            if verbose:
                print(f"  MCD43A2 quality layers not fetched: {exc}")
            warnings.warn(f"MCD43A2 quality layers not fetched ({exc}); continuing without them", stacklevel=2)

    p = Params(vals, transform, "EPSG:4326", used, qa, snow, path,
               {"collection": COLLECTION, "requested_date": date, "res_deg": f"{res:.8f}",
                "native_cells_per_output_cell": str(k),
                "bounds": ",".join(f"{b:.5f}" for b in bounds)})
    p.to_geotiff(path)
    if verbose:
        print(f"  MCD43A1 coverage {p.coverage() * 100:.1f} % of cells retrieved")
    return p
