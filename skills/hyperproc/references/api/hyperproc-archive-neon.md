# hyperproc.archive.neon

Release baseline **0.1.2**; source `hyperproc/archive/neon.py`. Choose a callable below rather than loading every declaration.

The NEON-backed part of :mod:`hyperproc.archive`, over the NEON Data API v0.

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

## Imported aliases

- `resolve` → `hyperproc.archive.collections.resolve`
- `Granule` → `hyperproc.archive.results.Granule`
- `Results` → `hyperproc.archive.results.Results`
- `plural` → `hyperproc.archive.results.plural`

## Declared callables and classes

- [_requests](symbols/hyperproc.archive.neon._requests.md) — internal
- [_get](symbols/hyperproc.archive.neon._get.md) — internal
- [token_from](symbols/hyperproc.archive.neon.token_from.md)
- [sites](symbols/hyperproc.archive.neon.sites.md)
- [_months](symbols/hyperproc.archive.neon._months.md) — internal
- [_hit](symbols/hyperproc.archive.neon._hit.md) — internal
- [search](symbols/hyperproc.archive.neon.search.md)
- [files](symbols/hyperproc.archive.neon.files.md)
- [_flight_time](symbols/hyperproc.archive.neon._flight_time.md) — internal
- [download](symbols/hyperproc.archive.neon.download.md)

## Constant expressions

- [BASE](constants/hyperproc.archive.neon.BASE.md)
- [ACCOUNT](constants/hyperproc.archive.neon.ACCOUNT.md)
- [NEEDS_TOKEN](constants/hyperproc.archive.neon.NEEDS_TOKEN.md)
- [DEFAULT_PATTERN](constants/hyperproc.archive.neon.DEFAULT_PATTERN.md)
- [_FLIGHTLINE](constants/hyperproc.archive.neon._FLIGHTLINE.md)
- [_SITES](constants/hyperproc.archive.neon._SITES.md)
