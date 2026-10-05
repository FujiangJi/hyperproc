# hyperproc.archive.neon.search

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def search(sensor: str, level: str | None=None, *, bbox=None, date=None, site: str | Sequence | None=None, count: int=100, site_radius_km: float=15.0, verbose: bool=True, **kwargs) -> Results
```

Find NEON AOP deliveries: one per site and month.

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

[Module and aliases](../hyperproc-archive-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.neon.search --runtime`.
