"""The NEON-backed part of :mod:`hyperproc.archive`, over the NEON Data API v0.

NEON does not publish granules the way a satellite mission does. It publishes
*deliveries*: one per site and month, holding every flightline flown in that
window - for the AOP spectrometer, often a hundred files and several hundred
gigabytes. So finding data here is two steps rather than one::

    >>> hits = hp.search("NEON", "L1", bbox=(-71.4, 44.0, -71.2, 44.2))
    >>> hits                     # deliveries, anonymous
    3 granules, size not published
    >>> lines = hp.archive.files(hits[0])      # the flightlines inside one
    >>> hp.download(lines[:2], "data/")

Searching is anonymous: site coordinates and the months each site was flown
come from ``/sites``, which is open. Listing and downloading files is not.
**Since June 2026 the NEON data endpoint requires an API token** - NEON's own
client says so in as many words - which is free from your account page at
https://data.neonscience.org/myaccount . Put it in ``NEON_TOKEN`` or pass
``token=``.

One caveat worth stating plainly: NEON publishes the site's coordinates but
not the flight box, so a delivery's footprint here is a point, and ``bbox=``
matches a site whose coordinates fall within ``site_radius_km`` of the box.
An AOP flight box is roughly 10 km across, so the default tolerance is 15 km.
"""
from __future__ import annotations

import fnmatch
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Sequence

from hyperproc.archive.collections import resolve
from hyperproc.archive.results import Granule, Results, plural

#: NEON Data API v0. Overridable for testing against a mirror.
BASE = os.environ.get("NEON_API_URL", "https://data.neonscience.org/api/v0/")

#: Where a token comes from, quoted in the error when there is none.
ACCOUNT = "https://data.neonscience.org/myaccount"

#: NEON's own wording, kept because it is the exact fact a user needs.
NEEDS_TOKEN = (
    "As of June 2026 the NEON API requires a token to list or download data "
    f"files. Searching does not. Get a free token from your account page at "
    f"{ACCOUNT}, then set NEON_TOKEN=... or pass token=..."
)

#: What a delivery is narrowed to by default, so a search hands back the files
#: :func:`hyperproc.open` reads rather than the whole month's paperwork.
DEFAULT_PATTERN = {"DP1.30006.001": "*_reflectance.h5"}

#: ``NEON_D01_BART_DP1_20190825_145110_reflectance.h5``
_FLIGHTLINE = re.compile(r"_(?P<date>\d{8})_(?P<time>\d{6})_")

_SITES: dict[str, dict] | None = None


def _requests():
    try:
        import requests
    except ImportError as exc:                     # pragma: no cover - environment
        raise ImportError(
            "searching NEON needs requests:\n    pip install 'hyperproc[search]'"
        ) from exc
    return requests


def _get(path: str, token: str | None = None, **params) -> dict:
    """One NEON API call, with the token where there is one."""
    requests = _requests()
    headers = {"accept": "application/json", "User-Agent": "hyperproc"}
    if token:
        headers["X-API-TOKEN"] = token
    r = requests.get(BASE + path, headers=headers, params=params or None, timeout=60)
    if r.status_code == 403:
        raise PermissionError(f"NEON refused {path} (403 Access Denied). {NEEDS_TOKEN}")
    if r.status_code == 404:
        raise FileNotFoundError(f"NEON has nothing at {path}")
    r.raise_for_status()
    return r.json()["data"]


def token_from(token: str | None = None) -> str | None:
    """The token to use: the argument, else ``NEON_TOKEN``, else none."""
    return token or os.environ.get("NEON_TOKEN") or None


def sites(refresh: bool = False) -> dict[str, dict]:
    """Every NEON site, keyed by code, with coordinates and what was flown there.

    One anonymous call answers both halves of a search, which is why the module
    uses it rather than ``/products``: each site carries ``siteLatitude``,
    ``siteLongitude`` and a ``dataProducts`` list whose entries name the months
    available. Cached for the process.
    """
    global _SITES
    if _SITES is None or refresh:
        _SITES = {s["siteCode"]: s for s in _get("sites")}
    return _SITES


def _months(date) -> tuple[str, str] | None:
    """``date=`` as an inclusive ``("YYYY-MM", "YYYY-MM")`` pair.

    A day is accepted and truncated to its month, because a delivery is monthly
    and pretending otherwise would drop the flight you asked for.
    """
    if date is None:
        return None
    if isinstance(date, str):
        date = (date, date)
    a, b = (str(d)[:7] for d in date)
    if not (re.fullmatch(r"\d{4}-\d{2}", a) and re.fullmatch(r"\d{4}-\d{2}", b)):
        raise ValueError(f"date must be YYYY-MM or YYYY-MM-DD, got {date!r}")
    return (a, b) if a <= b else (b, a)


def _hit(lat: float, lon: float, bbox, radius_km: float) -> bool:
    """Is the site within ``radius_km`` of the box?"""
    if bbox is None:
        return True
    w, s, e, n = bbox
    dlat = radius_km / 111.0
    dlon = dlat / max(0.05, abs(math.cos(math.radians(lat))))
    return (w - dlon) <= lon <= (e + dlon) and (s - dlat) <= lat <= (n + dlat)


def search(sensor: str, level: str | None = None, *, bbox=None, date=None,
           site: str | Sequence | None = None, count: int = 100,
           site_radius_km: float = 15.0, verbose: bool = True, **kwargs) -> Results:
    """Find NEON AOP deliveries: one per site and month.

    Args:
        sensor: ``"NEON"``.
        level: ``"L1"`` - flightline reflectance, DP1.30006.001. The mosaic
            tiles (DP3) exist but hyperproc's reader does not open them.
        bbox: ``(west, south, east, north)`` in degrees. Matches a site whose
            published coordinates lie within ``site_radius_km`` of the box;
            NEON publishes no flight-box polygon through the API.
        date: ``("YYYY-MM", "YYYY-MM")``, or one month, or full dates, which
            are truncated to their month. Deliveries are monthly.
        site: a four-letter site code, or several, instead of (or as well as)
            a box - ``"BART"``, ``["BART", "HARV"]``.
        count: cap on deliveries returned. ``-1`` for all of them.
        site_radius_km: how far outside ``bbox`` a site's coordinates may lie
            and still count. An AOP flight box is about 10 km across.
        verbose: print the query and the total.

    Returns:
        :class:`Results` of deliveries, newest first. Each has no size and no
        links: both need the file list, which needs a token. Pass one to
        :func:`files` to see the flightlines inside.
    """
    sensor, level, coll = resolve(sensor, level)
    if coll.backend != "neon":
        raise ValueError(f"{sensor} {level} is not a NEON product")
    if kwargs:
        raise TypeError(f"unexpected argument(s) {sorted(kwargs)} for a NEON search")

    window = _months(date)
    if bbox is not None:
        w, s, e, n = (float(v) for v in bbox)
        if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s <= 90 and -90 <= n <= 90):
            raise ValueError(f"bbox out of range: {bbox}; expected (west, south, east, north) in degrees")
        if w > e or s > n:
            raise ValueError(f"bbox is inside out: {bbox}; expected (west, south, east, north)")
        bbox = (w, s, e, n)
    wanted = ({site.upper()} if isinstance(site, str)
              else {str(x).upper() for x in site} if site is not None else None)

    query = {"product": coll.short_name, "bbox": bbox, "date": window, "site": site}
    if verbose:
        shown = {k: v for k, v in query.items() if v is not None and k != "product"}
        print(f"searching {coll.short_name} (NEON {level}){':' if shown else ''}"
              + "".join(f"\n    {k} = {v}" for k, v in shown.items()))

    out: list[Granule] = []
    for code, s_ in sorted(sites().items()):
        if wanted is not None and code not in wanted:
            continue
        lat, lon = s_.get("siteLatitude"), s_.get("siteLongitude")
        if lat is None or lon is None or not _hit(lat, lon, bbox, site_radius_km):
            continue
        for dp in s_.get("dataProducts", []):
            if dp.get("dataProductCode") != coll.short_name:
                continue
            for month in dp.get("availableMonths", []):
                if window and not (window[0] <= month <= window[1]):
                    continue
                out.append(Granule(
                    name=f"{coll.short_name}/{code}/{month}",
                    sensor=sensor, level=level, collection=coll.short_name,
                    version=coll.short_name.rsplit(".", 1)[-1],
                    time=datetime.strptime(month, "%Y-%m"),
                    bbox=(lon, lat, lon, lat), size_mb=None, cloud=None,
                    raw={"product": coll.short_name, "site": code, "month": month,
                         "siteName": s_.get("siteName"),
                         "releases": dp.get("availableReleases")},
                ))

    out.sort(key=lambda g: (g.time, g.name), reverse=True)
    if count is not None and count >= 0:
        out = out[:count]
    res = Results(out, query, note=coll.note)
    if verbose:
        print(f"  {res!r}")
        if not res:
            print("  note:", coll.note)
        else:
            print("  each is a whole site-month; hyperproc.archive.files() lists "
                  "the flightlines inside one (needs a NEON API token)")
    return res


def files(results, *, token: str | None = None, pattern: str | None = None,
          verbose: bool = True) -> Results:
    """List the files inside one or more deliveries.

    NEON has required a token for this since June 2026. One is sent when there
    is one; the request goes out either way, and a refusal comes back as a
    :class:`PermissionError` quoting the address a token comes from.

    Args:
        results: what :func:`search` returned, a list of deliveries, or one.
        token: the NEON API token. Defaults to ``NEON_TOKEN``.
        pattern: a shell glob over file names. The default keeps only what
            :func:`hyperproc.open` reads - ``*_reflectance.h5`` for
            DP1.30006.001 - because a delivery also carries flight logs,
            reports and quicklooks. ``"*"`` keeps everything.
        verbose: print what was found.

    Returns:
        :class:`Results`, one granule per file, with a real size and a link.

    The links NEON returns are signed and expire within the hour, so list and
    download in one sitting rather than pickling the result.
    """
    if isinstance(results, Granule):
        results = [results]
    # No pre-emptive check for a token. The endpoint is NEON's to open or close,
    # and refusing here would lock out anyone it does answer - a reopened
    # endpoint, an allow-listed network. Ask; let the 403 do the talking.
    tok = token_from(token)

    out: list[Granule] = []
    for d in results:
        raw = d.raw if isinstance(d, Granule) else d
        product, site, month = raw["product"], raw["site"], raw["month"]
        glob = pattern if pattern is not None else DEFAULT_PATTERN.get(product, "*")
        data = _get(f"data/{product}/{site}/{month}", token=tok)
        where = getattr(d, "bbox", None)
        for f in data.get("files", []):
            if not fnmatch.fnmatch(f["name"], glob):
                continue
            out.append(Granule(
                name=f["name"], sensor="NEON", level=getattr(d, "level", "L1"),
                collection=product, version=data.get("release"),
                time=_flight_time(f["name"]) or getattr(d, "time", None),
                bbox=where,
                size_mb=float(f.get("size") or 0) / 1e6, cloud=None,
                links=[f["url"]],
                raw={**raw, "file": f, "release": data.get("release")},
            ))

    res = Results(out, {"pattern": pattern, "deliveries": len(list(results))})
    if verbose:
        print(f"  {res!r}")
        if not res:
            print(f"  note: nothing matched {pattern!r}; pass pattern='*' to see "
                  "everything the delivery holds")
    return res


def _flight_time(name: str) -> datetime | None:
    m = _FLIGHTLINE.search(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group("date") + m.group("time"), "%Y%m%d%H%M%S")
    except ValueError:                             # pragma: no cover - defensive
        return None


def download(results, out_dir: str | Path = "data", workers: int = 4,
             token: str | None = None, pattern: str | None = None,
             verbose: bool = True) -> list[Path]:
    """Fetch NEON files into ``out_dir``. NEON requires a token for this.

    Deliveries are expanded to their files first, so passing what
    :func:`search` returned downloads a whole site-month - often hundreds of
    gigabytes. The total is printed before anything is fetched; narrow it with
    :func:`files` and a slice, or with ``pattern=``.
    """
    requests = _requests()
    if isinstance(results, Granule):
        results = [results]
    items = list(results)
    tok = token_from(token)

    deliveries = [g for g in items if isinstance(g, Granule) and not g.links]
    if deliveries:
        items = [g for g in items if g not in deliveries]
        items += list(files(deliveries, token=tok, pattern=pattern, verbose=False))
    if not items:
        if verbose:
            print("nothing to download")
        return []

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    total = sum(g.size_mb or 0.0 for g in items) / 1024.0
    if verbose:
        print(f"downloading {plural(len(items), 'file')} "
              f"({total:,.1f} GB) -> {out}")

    def fetch(g: Granule) -> Path:
        dest = out / g.name
        # a finished file is left alone; a half-written .part never becomes one
        if dest.exists() and g.size_mb and abs(dest.stat().st_size / 1e6 - g.size_mb) < 1:
            if verbose:
                print(f"  have {g.name}")
            return dest
        with requests.get(g.links[0], stream=True, timeout=300) as r:
            if r.status_code == 403:
                raise PermissionError(
                    f"NEON refused {g.name} (403). Signed links expire within the "
                    f"hour - list again with hyperproc.archive.files(). {NEEDS_TOKEN}")
            r.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
            tmp.replace(dest)
        if verbose:
            print(f"  {g.name}  {(g.size_mb or 0):,.0f} MB")
        return dest

    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        paths = list(pool.map(fetch, items))

    if verbose:
        print(f"  {plural(len(paths), 'file')} in {out}")
    return paths
