"""The CMR-backed half of :mod:`hyperproc.archive`, over ``earthaccess``."""
from __future__ import annotations

from datetime import datetime
import warnings
from pathlib import Path
from typing import Any

from hyperproc.archive.collections import resolve
from hyperproc._ncrc import rc_warning, unterminated_rc_files
from hyperproc.archive.results import Granule, Results, plural

#: Earthdata login page, quoted in the error when a download has no credentials.
URS = "https://urs.earthdata.nasa.gov"


def _earthaccess():
    try:
        import earthaccess
    except ImportError as exc:                     # pragma: no cover - environment
        raise ImportError(
            "searching archives needs earthaccess:\n"
            "    pip install 'hyperproc[search]'\n"
            f"Downloads also need a free Earthdata login ({URS}); searching does not."
        ) from exc
    return earthaccess


def _bbox_of(umm: dict) -> tuple[float, float, float, float] | None:
    """The granule footprint as ``(west, south, east, north)``.

    CMR states the footprint as a polygon, which is the honest shape for a
    rotated swath, but a box is what a listing can show and what a map needs.
    """
    geom = (umm.get("SpatialExtent", {})
               .get("HorizontalSpatialDomain", {})
               .get("Geometry", {}))
    pts: list[dict] = []
    for poly in geom.get("GPolygons", []):
        pts += poly.get("Boundary", {}).get("Points", [])
    for rect in geom.get("BoundingRectangles", []):
        return (rect["WestBoundingCoordinate"], rect["SouthBoundingCoordinate"],
                rect["EastBoundingCoordinate"], rect["NorthBoundingCoordinate"])
    if not pts:
        return None
    lon = [p["Longitude"] for p in pts]
    lat = [p["Latitude"] for p in pts]
    return (min(lon), min(lat), max(lon), max(lat))


def _browse_of(umm: dict) -> str | None:
    """A quicklook a browser can load, or ``None``.

    CMR lists the same image twice, once over https and once as an ``s3://``
    URI that nothing outside AWS can open, so only the https one is any use on
    a map. Some collections list a browse that was never written - PACE's all
    404 - which is a property of the archive, not something to paper over.
    """
    for u in umm.get("RelatedUrls", []) or []:
        if "VISUALIZATION" in (u.get("Type") or "") and str(u.get("URL", "")).startswith("http"):
            return u["URL"]
    return None


def _time_of(umm: dict) -> datetime | None:
    t = umm.get("TemporalExtent", {})
    raw = (t.get("RangeDateTime", {}).get("BeginningDateTime")
           or t.get("SingleDateTime"))
    if not raw:
        return None
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)


def search(sensor: str, level: str | None = None, *, bbox=None, date=None,
           cloud: tuple[float, float] | None = None, version: str | None = None,
           count: int = 100, verbose: bool = True, **kwargs) -> Results:
    """Find granules.

    Args:
        sensor: ``"EMIT"``, ``"PACE"``, ``"AVIRIS-3"``, ``"AVIRIS-5"``. The
            reader spellings work too (``"aviris3"``).
        level: ``"L1B"`` for radiance, ``"L2A"``/``"L2"`` for reflectance.
            Required where a sensor has more than one searchable level.
        bbox: ``(west, south, east, north)`` in degrees.
        date: ``("YYYY-MM-DD", "YYYY-MM-DD")``, or a single date for one day.
        cloud: ``(min, max)`` percent. Only where the provider reports it -
            EMIT and PACE do, the AVIRIS collections do not, and asking for a
            range there would silently drop every granule.
        version: a collection version. **Left open by default on purpose**:
            EMIT carries two live versions and pinning one hides the other.
        count: cap on granules returned. ``-1`` for everything CMR has.
        verbose: print the query and the total.

    Returns:
        :class:`Results`, ordered as CMR returned them.
    """
    ea = _earthaccess()
    sensor, level, coll = resolve(sensor, level)

    query: dict[str, Any] = {"short_name": coll.short_name}
    if version is not None:
        query["version"] = str(version)
    if bbox is not None:
        w, s, e, n = (float(v) for v in bbox)
        if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s <= 90 and -90 <= n <= 90):
            raise ValueError(f"bbox out of range: {bbox}; expected (west, south, east, north) in degrees")
        if w > e or s > n:
            raise ValueError(f"bbox is inside out: {bbox}; expected (west, south, east, north)")
        query["bounding_box"] = (w, s, e, n)
    if date is not None:
        query["temporal"] = (date, date) if isinstance(date, str) else tuple(date)
    if cloud is not None:
        if not coll.cloud:
            raise ValueError(
                f"{sensor} {level} does not report cloud cover ({coll.short_name} "
                f"carries no CloudCover field), so cloud={tuple(cloud)} would exclude "
                f"every granule rather than filtering them. Drop it.")
        query["cloud_cover"] = tuple(cloud)
    query.update(kwargs)

    if verbose:
        shown = {k: v for k, v in query.items() if k != "short_name"}
        print(f"searching {coll.short_name} ({sensor} {level}){':' if shown else ''}"
              + "".join(f"\n    {k} = {v}" for k, v in shown.items()))

    found = ea.search_data(count=count, **query)
    out = Results((_granule(r, sensor, level, coll.short_name) for r in found), query)
    if verbose:
        print(f"  {out!r}")
        if not out:
            if coll.note:
                print("  note:", coll.note)
    return out


def _granule(raw, sensor: str, level: str, short_name: str) -> Granule:
    umm = raw["umm"]
    cloud = umm.get("CloudCover")
    return Granule(
        name=umm.get("GranuleUR", "?"),
        sensor=sensor, level=level, collection=short_name,
        version=(umm.get("CollectionReference") or {}).get("Version"),
        time=_time_of(umm), bbox=_bbox_of(umm),
        size_mb=float(getattr(raw, "size", 0.0) or 0.0),
        cloud=float(cloud) if cloud is not None else None,
        links=list(raw.data_links() or []), browse=_browse_of(umm), raw=raw,
    )


def download(results, out_dir: str | Path = "data", workers: int = 8,
             verbose: bool = True) -> list[Path]:
    """Fetch granules into ``out_dir``.

    Args:
        results: a :class:`Results`, a list of :class:`Granule`, or one granule.
        out_dir: created if missing. Everything lands flat, which is what the
            readers expect - they find a granule's siblings by name.
        workers: parallel connections.

    Returns:
        the downloaded paths.

    Needs a free Earthdata login; ``earthaccess`` reads ``~/.netrc`` or the
    ``EARTHDATA_USERNAME``/``EARTHDATA_PASSWORD`` variables, else asks once.
    """
    ea = _earthaccess()
    if isinstance(results, Granule):
        results = [results]
    granules = [g.raw if isinstance(g, Granule) else g for g in results]
    if not granules:
        if verbose:
            print("nothing to download")
        return []

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    total = sum(float(getattr(g, "size", 0.0) or 0.0) for g in granules) / 1024.0
    if verbose:
        print(f"downloading {plural(len(granules), 'granule')} "
              f"({total:,.1f} GB) -> {out}")

    try:
        ea.login()
    except Exception as exc:                       # pragma: no cover - environment
        raise RuntimeError(
            f"Earthdata login failed ({exc}). Register free at {URS}, then run\n"
            "    python -c \"import earthaccess; earthaccess.login(persist=True)\"\n"
            "once - it asks for the username and password and writes ~/.netrc - or set "
            "EARTHDATA_USERNAME and EARTHDATA_PASSWORD instead."
        ) from exc

    # earthaccess writes ~/.dodsrc here, without a trailing newline, and that
    # is what makes netCDF4 crash later inside ISOFIT. Catch it at the source.
    bad = unterminated_rc_files()
    if bad:
        warnings.warn(rc_warning(bad), RuntimeWarning, stacklevel=2)

    files = ea.download(granules, local_path=str(out), threads=workers)
    paths = [Path(f) for f in files if f]
    if verbose:
        print(f"  {plural(len(paths), 'file')} in {out}")
    return paths
