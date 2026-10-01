"""Turn a swath into a map-projected grid.

Sensors that ship per-pixel latitude/longitude instead of an affine transform
(PRISMA L1/L2B/L2C, PACE, un-orthorectified EMIT) cannot be written to GeoTIFF
directly: their ground track is rotated and slightly curved, so no single
six-number transform describes it. PRISMA's L2C swath, for instance, runs about
79 degrees off north.

:func:`georeference` resamples such a dataset onto a regular north-up grid by
building a **GLT** (geometry lookup table) - the same device EMIT ships in its
own granules, and what prismaread's ``base_georef`` produces. Every output pixel
is a *verbatim copy* of one input pixel: nearest-neighbour by construction, so
no spectra are invented by interpolation.
"""

from __future__ import annotations

import numpy as np
import xarray as xr


#: Per-sensor default output resolution, in the units of the target CRS.
#: PACE grids to EPSG:4326, so this is degrees: 0.01 deg is ~1.1 km, matching
#: OCI's ~1140 m nadir pixel. A measured median would be ~0.0174 deg here,
#: because pixels grow to 5600 m at 71 deg view zenith - defensible on average
#: but it coarsens the near-nadir fifth of the swath, where the data is best,
#: and makes the output resolution depend on which part of the swath you got.
#: This also reproduces what read_pace_to_geotiff.py produced.
DEFAULT_RESOLUTION_DEG = {"PACE": 0.01}


def utm_epsg(lon: float, lat: float) -> int:
    """EPSG code of the UTM zone containing a point (zone 60 at lon = 180,
    with the Norway and Svalbard exceptions of the UTM grid)."""
    lon = ((lon + 180.0) % 360.0) - 180.0
    zone = min(int((lon + 180.0) // 6.0) + 1, 60)
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone = 32
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone = 31
        elif 9.0 <= lon < 21.0:
            zone = 33
        elif 21.0 <= lon < 33.0:
            zone = 35
        elif 33.0 <= lon < 42.0:
            zone = 37
    return (32600 if lat >= 0 else 32700) + zone


def georeference(
    ds: xr.Dataset,
    epsg: int | None = None,
    resolution: float | None = None,
    radius: float | None = None,
    fill_holes: bool = True,
    like: xr.Dataset | None = None,
) -> xr.Dataset:
    """Resample a lat/lon swath onto a regular projected grid.

    Args:
        ds: dataset carrying 2-D ``lat`` and ``lon`` variables.
        epsg: target CRS. Defaults to the UTM zone under the scene centre,
            which for PRISMA reproduces the zone ASI uses for its own L2D.
            Pass ``4326`` for plate carree.
        resolution: output pixel size in target-CRS units. ``None`` uses the
            sensor's documented default where one exists - PACE gets 0.01 deg
            (~1.1 km), matching its nadir pixel - and otherwise measures the
            median spacing between adjacent swath pixels, which for PRISMA
            lands on ~30 m. Pass ``"native"`` to always measure, or a number
            to set it yourself.
        radius: hard upper bound of the search, in metres. Defaults to twice
            the 99th-percentile source pixel half-diagonal.
        fill_holes: a cell is filled when its nearest source pixel lies within
            that pixel's own half-diagonal (its footprint), so gaps where the
            grid is finer than the swath close, while nothing is invented past
            the swath edge or the along-track ends. ``False`` accepts only
            source pixels inside the cell itself.
        like: a projected dataset whose grid to reproduce exactly (CRS,
            pixel size, origin and shape), for example ASI's PRISMA L2D, so
            the result compares cell for cell. Overrides ``epsg`` and
            ``resolution``; north-up grids only.

    Returns:
        A new Dataset on ``(y, x)`` with ``crs``/``transform`` set, ready for
        :func:`hyperproc.to_geotiff`. ``lat``/``lon`` are dropped; a ``valid``
        mask marks cells the swath actually covers.

    Raises:
        ValueError: ``ds`` has no ``lat``/``lon``, or is already projected.
    """
    from pyproj import Transformer

    if "lat" not in ds or "lon" not in ds:
        raise ValueError(
            "georeference() needs 2-D lat/lon variables. Open the granule with "
            "latlon=True, or - if it is already projected - just call to_geotiff()."
        )
    if "crs" in ds.attrs:
        raise ValueError(f"dataset is already projected ({ds.attrs['crs']})")

    lat = np.asarray(ds["lat"].values, dtype="float64")
    lon = np.asarray(ds["lon"].values, dtype="float64")
    ok = np.isfinite(lat) & np.isfinite(lon)
    if not ok.any():
        raise ValueError("lat/lon are entirely non-finite")
    unwrapped = False
    if float(np.nanmax(lon) - np.nanmin(lon)) > 180.0:
        # The swath crosses the antimeridian: keep longitudes continuous
        # (0..360 on the far side) so the extent, spacing and zone are those
        # of the swath, not of the whole globe.
        lon = np.where(lon < 0.0, lon + 360.0, lon)
        unwrapped = True

    ref = None
    if like is not None:
        crs = str(like.attrs.get("crs", ""))
        gt = like.attrs.get("transform")
        if not crs.upper().startswith("EPSG:") or gt is None:
            raise ValueError("like= needs a projected dataset with an EPSG crs and a transform")
        gt = [float(v) for v in gt]
        if gt[2] or gt[4]:
            raise ValueError("like= supports north-up reference grids only")
        epsg = int(crs.split(":")[1])
        resolution = abs(gt[1])
        ref = (gt, like.sizes["x"], like.sizes["y"])
    if epsg is None:
        span = float(np.nanmax(lon) - np.nanmin(lon))
        if span > 6.0:
            # Wider than one UTM zone. A PACE granule spans ~35 degrees, and
            # forcing that into a single zone distorts the edges badly, so fall
            # back to plate carree.
            epsg = 4326
        else:
            epsg = utm_epsg(float(np.nanmedian(lon)), float(np.nanmedian(lat)))

    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    sx, sy = tf.transform(lon, lat)
    sx = np.where(ok, sx, np.nan)
    sy = np.where(ok, sy, np.nan)

    if resolution == "native":
        resolution = _native_spacing(sx, sy)
    elif resolution is None:
        # A per-sensor default only makes sense in the CRS it was quoted for.
        default = DEFAULT_RESOLUTION_DEG.get(str(ds.attrs.get("sensor", "")).upper())
        resolution = default if (default is not None and epsg == 4326) \
            else _native_spacing(sx, sy)

    if ref is not None:
        gt, nx, ny = ref
        xs = gt[0] + gt[1] / 2 + np.arange(nx) * gt[1]          # cell centres of the reference grid
        ys = gt[3] + gt[5] / 2 + np.arange(ny) * gt[5]
        transform = tuple(gt)
    else:
        x0, x1 = np.nanmin(sx), np.nanmax(sx)
        y0, y1 = np.nanmin(sy), np.nanmax(sy)
        nx = int(np.ceil((x1 - x0) / resolution)) + 1
        ny = int(np.ceil((y1 - y0) / resolution)) + 1
        xs = x0 + np.arange(nx) * resolution
        ys = y1 - np.arange(ny) * resolution
        transform = (x0 - resolution / 2, resolution, 0.0, y1 + resolution / 2, 0.0, -resolution)

    gx, gy = np.meshgrid(xs, ys)
    glt = _nearest_glt(lat, lon, gx, gy, ok, epsg, radius, resolution, fill_holes)
    valid = glt >= 0

    out = xr.Dataset(
        # Carry only coords that do not live on the spatial dims: the output
        # grid has a different y/x size, so a per-scan-line coordinate such as
        # PACE's scan_time would collide with the resampled cube.
        coords={k: v for k, v in ds.coords.items()
                if k not in ("x", "y") and not ({"y", "x"} & set(v.dims))},
        attrs={**ds.attrs,
               "crs": f"EPSG:{epsg}",
               "transform": transform,
               "orthorectified": 1,
               "regridded_from": "swath lat/lon via GLT nearest-neighbour"
                                 + (f" onto the grid of {like.attrs.get('granule', 'the reference')}" if ref else ""),
               "resolution": float(resolution),
               **({"lon_unwrapped": "longitudes east of the antimeridian are 180..360"} if unwrapped else {})},
    )
    for name, da in ds.data_vars.items():
        if name in ("lat", "lon"):
            continue
        if da.dims[:2] != ("y", "x"):
            out[name] = da
            continue
        if da.ndim == 3 and hasattr(da.data, "dask"):
            # Lazy gather, one band group at a time: the full PACE L2 cube
            # would otherwise cost ~10 GB of temporaries in memory.
            import dask.array as dsk
            nb_per = max(1, int(3e8 // (ny * nx * max(da.dtype.itemsize, 4))))
            src = da.data.rechunk({0: -1, 1: -1, 2: nb_per})
            out_dtype = da.dtype if da.dtype.kind in "biu" else np.dtype("float32")
            arr = dsk.map_blocks(lambda b: _apply_glt(b, glt, valid), src, dtype=out_dtype,
                                 chunks=((ny,), (nx,), src.chunks[2]))
            out[name] = (da.dims, arr)
        else:
            out[name] = (da.dims, _apply_glt(np.asarray(da.values), glt, valid))
        out[name].attrs = dict(da.attrs)

    out["valid"] = (("y", "x"), valid)
    out["valid"].attrs["long_name"] = "output cell covered by the swath"
    out.coords["x"] = ("x", xs)
    out.coords["y"] = ("y", ys)
    out["x"].attrs.update(units="m" if epsg != 4326 else "degrees_east")
    out["y"].attrs.update(units="m" if epsg != 4326 else "degrees_north")

    # Rebuild lat/lon from the output cell centres rather than gathering the
    # source values through the GLT: this is exact for every cell, including
    # ones filled by the hole pass.
    lat_g, lon_g = latlon_grid(out)
    out["lat"] = (("y", "x"), np.where(valid, lat_g, np.nan).astype("float32"))
    out["lon"] = (("y", "x"), np.where(valid, lon_g, np.nan).astype("float32"))
    out["lat"].attrs.update(units="degrees_north", long_name="latitude")
    out["lon"].attrs.update(units="degrees_east", long_name="longitude")
    return out


def latlon_grid(ds: xr.Dataset) -> tuple[np.ndarray, np.ndarray]:
    """WGS-84 ``(lat, lon)`` of every cell centre of a projected dataset.

    Derived from the CRS and the full affine transform, so it is exact even
    where the granule ships no geolocation arrays - including the rotated,
    flight-aligned AVIRIS grids, where the 1-D ``x``/``y`` coordinates describe
    only the top row and left column. The affine is rebuilt from the
    coordinates the same way the GeoTIFF writer does, so subsets stay right.
    """
    from pyproj import Transformer

    if "crs" not in ds.attrs:
        raise ValueError("dataset is not projected; use its own lat/lon arrays")
    from hyperproc.io import _transform_for
    aff = _transform_for(ds) if ds.attrs.get("transform") else None
    if aff is not None:
        rows, cols = np.mgrid[0:ds.sizes["y"], 0:ds.sizes["x"]] + 0.5   # pixel centres
        xx = aff.c + aff.a * cols + aff.b * rows
        yy = aff.f + aff.d * cols + aff.e * rows
    else:
        xx, yy = np.meshgrid(np.asarray(ds["x"].values), np.asarray(ds["y"].values))
    lon, lat = Transformer.from_crs(ds.attrs["crs"], 4326,
                                    always_xy=True).transform(xx, yy)
    return lat, lon


def _ecef(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Sphere-surface cartesian metres, so a KD-tree measures real distance.

    Doing the search in degrees would distort badly over a swath spanning 23
    degrees of latitude, where a degree of longitude shrinks by a third.
    """
    R = 6371000.0
    la, lo = np.radians(lat), np.radians(lon)
    cla = np.cos(la)
    return np.column_stack([(R * cla * np.cos(lo)).ravel(),
                            (R * cla * np.sin(lo)).ravel(),
                            (R * np.sin(la)).ravel()])


def _nearest_glt(lat, lon, gx, gy, ok, epsg, radius, resolution, fill_holes):
    """Nearest source pixel per output cell, rejected beyond ``radius``.

    This is what pyresample's ``radius_of_influence`` does. Dilating a
    forward-mapped GLT instead - the obvious cheap approach - fails twice on a
    wide swath: it smears the edge pixel outward past the real swath boundary,
    and it still cannot reach across the gaps where pixels are widest.
    """
    from pyproj import Transformer
    from scipy.spatial import cKDTree

    src_ok = np.flatnonzero(ok.ravel())
    src = _ecef(lat, lon)[src_ok]

    # Output cell centres back to lon/lat, then to the same cartesian frame.
    if epsg == 4326:
        glon, glat = gx, gy
    else:
        glon, glat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(gx, gy)
    tgt = _ecef(glat, glon)
    # Each source pixel's own footprint: half the diagonal spanned by its
    # along-scan and along-track neighbours. A single global radius (the old
    # 99th-percentile spacing) reached 3-6 km past the along-track ends of a
    # PACE granule and invented ~0.8 % of the cells.
    P = _ecef(lat, lon).reshape(lat.shape + (3,))
    dx = np.linalg.norm(np.diff(P, axis=1), axis=-1)
    dx = np.concatenate([dx, dx[:, -1:]], axis=1)
    dy = np.linalg.norm(np.diff(P, axis=0), axis=-1)
    dy = np.concatenate([dy, dy[-1:, :]], axis=0)
    hd = (0.5 * np.hypot(dx, dy)).ravel()[src_ok]
    good = np.isfinite(hd) & (hd > 0)
    hd = np.where(good, hd, np.nanmedian(hd[good]) if good.any() else 1000.0)
    res_m = resolution * 111320.0 if epsg == 4326 else resolution
    upper = float(radius) if radius is not None else 2.0 * float(np.percentile(hd, 99))
    dist, idx = cKDTree(src).query(tgt, k=1, distance_upper_bound=upper, workers=-1)
    hit = np.isfinite(dist)
    thr = np.full(tgt.shape[0], 0.7071067811865476 * res_m)      # the cell's own half-diagonal
    if fill_holes:
        thr[hit] = np.maximum(thr[hit], hd[idx[hit]])
    if radius is not None:
        thr = np.minimum(thr, float(radius))
    accept = hit & (dist <= thr)
    out = np.full(tgt.shape[0], -1, dtype="int64")
    out[accept] = src_ok[idx[accept]]
    return out.reshape(gx.shape)


def _native_spacing(sx: np.ndarray, sy: np.ndarray) -> float:
    """Median distance between horizontally adjacent swath pixels."""
    dx = np.diff(sx, axis=1)
    dy = np.diff(sy, axis=1)
    d = np.hypot(dx, dy)
    d = d[np.isfinite(d) & (d > 0)]
    if d.size == 0:
        raise ValueError("cannot infer resolution from lat/lon; pass resolution=")
    return float(np.median(d))


def _apply_glt(arr: np.ndarray, glt: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Gather source pixels into the output grid. 2-D or 3-D, NaN outside."""
    ny, nx = glt.shape
    src = arr.reshape(-1, *arr.shape[2:])
    idx = np.where(valid, glt, 0)

    if arr.dtype.kind == "b":
        out = np.zeros((ny, nx) + arr.shape[2:], dtype=bool)
        out[valid] = src[idx[valid]]
        return out
    if arr.dtype.kind in "iu":
        # Flag words (PACE l2_flags, int64) must keep every bit; 0 outside.
        out = np.zeros((ny, nx) + arr.shape[2:], dtype=arr.dtype)
        out[valid] = src[idx[valid]]
        return out
    out = np.full((ny, nx) + arr.shape[2:], np.nan, dtype="float32")
    out[valid] = src[idx[valid]].astype("float32", copy=False)
    return out
