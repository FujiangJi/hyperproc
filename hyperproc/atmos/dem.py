"""Surface elevation for products that ship none, from the Copernicus DEM.

ISOFIT needs a height for every pixel (it sets the pressure altitude of the
look-up table). EMIT, PACE and the AVIRIS products carry one; DESIS, EnMAP,
Tanager and PRISMA do not. This module samples the Copernicus DEM GLO-30
(30 m, TanDEM-X, heights above the EGM2008 geoid, global except a handful of
countries that are only released at 90 m) from its public cloud-optimised
GeoTIFF tiles on AWS, one 1 x 1 degree tile at a time, and keeps the tiles
under ``$HYPERPROC_CACHE_DIR/dem`` so a region is fetched once.

Heights are above the EGM2008 geoid, which is what a pressure altitude
wants; the JPL products (EMIT, AVIRIS) carry ellipsoidal heights instead, so
the two differ by the local geoid undulation (about 36 m on the EMIT test
granule off California), which changes the surface pressure by under 0.5 %.

Tiles that do not exist (open ocean, or the excluded countries at 30 m) fall
back to GLO-90 and then to sea level. Scenes that would need more than
``MAX_TILES_30`` tiles (a PACE granule spans 20 degrees) are sampled from
GLO-90 outright; at kilometre pixels that loses nothing.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
import warnings
from pathlib import Path

import numpy as np

SOURCES = {30: ("copernicus-dem-30m", "Copernicus_DSM_COG_10"),
           90: ("copernicus-dem-90m", "Copernicus_DSM_COG_30")}
MAX_TILES_30 = 60


def cache_dir() -> Path:
    d = Path(os.environ.get("HYPERPROC_CACHE_DIR", "~/.cache/hyperproc")).expanduser() / "dem"
    d.mkdir(parents=True, exist_ok=True)
    return d


def tile_id(lat0: int, lon0: int, resolution: int = 30) -> str:
    """Copernicus tile name for the 1-degree cell whose south-west corner is (lat0, lon0)."""
    prefix = SOURCES[resolution][1]
    ns = "N" if lat0 >= 0 else "S"
    ew = "E" if lon0 >= 0 else "W"
    return f"{prefix}_{ns}{abs(lat0):02d}_00_{ew}{abs(lon0):03d}_00_DEM"


def tile_url(lat0: int, lon0: int, resolution: int = 30) -> str:
    tid = tile_id(lat0, lon0, resolution)
    return f"https://{SOURCES[resolution][0]}.s3.amazonaws.com/{tid}/{tid}.tif"


def fetch_tile(lat0: int, lon0: int, resolution: int = 30, verbose: bool = False) -> Path | None:
    """The cached tile file, downloading it on first use; None when the tile does not exist."""
    dest = cache_dir() / f"{tile_id(lat0, lon0, resolution)}.tif"
    marker = dest.with_suffix(".missing")
    if dest.is_file():
        return dest
    if marker.is_file():
        return None
    url = tile_url(lat0, lon0, resolution)
    tmp = dest.with_suffix(".part")
    try:
        if verbose:
            print(f"dem: fetching {url}", flush=True)
        urllib.request.urlretrieve(url, tmp)
    except urllib.error.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        if exc.code in (403, 404):
            marker.touch()
            return None
        raise
    tmp.rename(dest)
    return dest


def _read_tile(path: Path):
    import rasterio
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        nodata = src.nodata
        tr = src.transform
    if nodata is not None:
        arr[arr == nodata] = np.nan
    return arr, tr


def sample(lat, lon, resolution: int = 30, fallback: bool = True, verbose: bool = False) -> np.ndarray:
    """Elevation (m above EGM2008) at every (lat, lon), bilinear within each tile.

    NaN where the coordinates are not finite; 0 where no tile exists (sea).
    """
    from scipy.ndimage import map_coordinates

    lat = np.asarray(lat, dtype="float64")
    lon = np.asarray(lon, dtype="float64")
    lon = np.where(lon >= 180.0, lon - 360.0, lon)
    out = np.full(lat.shape, np.nan, dtype="float32")
    ok = np.isfinite(lat) & np.isfinite(lon)
    if not ok.any():
        return out
    la0 = np.floor(lat[ok]).astype(int)
    lo0 = np.floor(lon[ok]).astype(int)
    tiles = np.unique(np.stack([la0, lo0], axis=1), axis=0)
    if resolution == 30 and len(tiles) > MAX_TILES_30:
        warnings.warn(f"{len(tiles)} DEM tiles needed; sampling GLO-90 instead of GLO-30", stacklevel=2)
        resolution = 90
    idx_ok = np.flatnonzero(ok.ravel())
    lat_ok, lon_ok = lat.ravel()[idx_ok], lon.ravel()[idx_ok]
    flat = out.ravel()
    for a0, o0 in tiles:
        m = (la0 == a0) & (lo0 == o0)
        path = fetch_tile(int(a0), int(o0), resolution, verbose)
        if path is None and fallback and resolution == 30:
            path = fetch_tile(int(a0), int(o0), 90, verbose)
        if path is None:
            flat[idx_ok[m]] = 0.0                     # open ocean: no tile is published
            continue
        arr, tr = _read_tile(path)
        col = (lon_ok[m] - tr.c) / tr.a - 0.5
        row = (lat_ok[m] - tr.f) / tr.e - 0.5
        vals = map_coordinates(arr, [row, col], order=1, mode="nearest")
        flat[idx_ok[m]] = np.where(np.isfinite(vals), vals, 0.0)
    return flat.reshape(lat.shape)


def add_elevation(ds, resolution: int = 30, name: str = "elev", overwrite: bool = False, verbose: bool = True):
    """Attach a DEM-sampled ``elev (y, x)`` layer to a dataset that has none.

    Uses the dataset's ``lat``/``lon`` layers, or derives them from the map
    grid when the dataset is projected. Returns the dataset (modified in place).
    """
    if name in ds and not overwrite:
        return ds
    if "lat" in ds and "lon" in ds:
        lat, lon = np.asarray(ds["lat"].values, "float64"), np.asarray(ds["lon"].values, "float64")
    elif "crs" in ds.attrs:
        from hyperproc.grid import latlon_grid
        lat, lon = latlon_grid(ds)
    else:
        raise ValueError("dataset has neither lat/lon layers nor a CRS; cannot place it on the DEM")
    elev = sample(lat, lon, resolution=resolution, verbose=verbose)
    ds[name] = (("y", "x"), elev.astype("float32"))
    src = f"Copernicus DEM GLO-{resolution} (EGM2008), bilinear"
    ds[name].attrs.update(units="m", long_name="surface elevation", source=src)
    ds.attrs["elev_source"] = src
    if verbose:
        print(f"dem: elev {np.nanmin(elev):.0f}..{np.nanmax(elev):.0f} m from {src}")
    return ds
