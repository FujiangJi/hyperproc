"""Find and fetch granules, so a workflow can start from a place and a date.

``hyperproc.open`` reads a file you already have. This finds the file.

    >>> hits = hp.search("EMIT", "L2A", bbox=(-121, 34, -119.8, 35.1),
    ...                  date=("2023-04-20", "2023-04-25"))
    >>> hits
    3 granules, 14.1 GB
    >>> hp.download(hits[:1], "data/")

Three archives answer, picked by what you asked for:

* **NASA CMR** for EMIT, PACE and AVIRIS-3/-5, over ``earthaccess``. Downloads
  need a free Earthdata login (https://urs.earthdata.nasa.gov).
* **NEON's Data API** for AOP flightlines. NEON publishes a site-month at a
  time, so :func:`files` opens one up into the flightlines inside. Downloads
  need a NEON API token (https://data.neonscience.org/myaccount), required
  since June 2026.
* **DLR's EOC Geoservice STAC** for EnMAP and DESIS. Downloads need a free EOC
  account (https://sso.eoc.dlr.de/).

Searching all three is anonymous. PRISMA, Tanager, AVIRIS-NG and AVIRIS
Classic are not searchable from here at all; asking for one raises with the
address rather than returning an empty list. :func:`describe` prints the whole
picture, and :func:`hyperproc.search_map` does it on a map you can draw on.
"""
from __future__ import annotations

from hyperproc.archive.api import can_download, credentials, download, files, search
from hyperproc.archive.collections import (BACKENDS, COLLECTIONS, ELSEWHERE, Collection,
                                           describe, resolve)
from hyperproc.archive.results import Granule, Results

__all__ = ["search", "download", "files", "describe", "credentials",
           "can_download", "Granule", "Results",
           "COLLECTIONS", "ELSEWHERE", "BACKENDS", "Collection", "resolve",
           "search_map", "Map"]


def __getattr__(name):
    # leafmap and ipyleaflet are a heavy optional extra; importing hyperproc
    # should not pay for them, so the map arrives only when it is asked for
    if name in ("Map", "search_map"):
        from hyperproc.archive import interactive
        return getattr(interactive, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
