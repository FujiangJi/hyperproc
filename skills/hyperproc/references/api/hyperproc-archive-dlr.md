# hyperproc.archive.dlr

Release baseline **0.1.2**; source `hyperproc/archive/dlr.py`. Choose a callable below rather than loading every declaration.

The DLR-backed part of :mod:`hyperproc.archive`: EnMAP and DESIS, over STAC.

EnMAP and DESIS are not in NASA's CMR. DLR's Earth Observation Center runs its
own STAC catalogue at https://geoservice.dlr.de/, and it is fully open to
search - 238,494 EnMAP L2A scenes and 14,958 DESIS L2A scenes, each with a
footprint polygon, a cloud fraction and a per-file asset list::

    >>> hits = hp.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5),
    ...                  date=("2023-06-01", "2023-09-30"), cloud=(0, 10))
    >>> hp.download(hits[:1], "data/")

Downloading is not open: the file server redirects to DLR's CAS single sign-on,
and takes no HTTP Basic auth, so :func:`download` carries the login form
through once per mission and keeps the session cookie. Access is granted per
mission - EnMAP at https://www.enmap.org/data_access/, DESIS through EOWEB at
https://eoweb.dlr.de/egp/ - so the two accounts need not be the same; see
:func:`credentials`.

DLR publishes the rasters as cloud-optimised GeoTIFFs, whose names carry an
extra ``_COG`` before the extension. hyperproc's EnMAP reader accepts both
spellings, so a downloaded granule opens with no renaming.

## Imported aliases

- `resolve` → `hyperproc.archive.collections.resolve`
- `Granule` → `hyperproc.archive.results.Granule`
- `Results` → `hyperproc.archive.results.Results`
- `plural` → `hyperproc.archive.results.plural`

## Declared callables and classes

- [needs_login](symbols/hyperproc.archive.dlr.needs_login.md)
- [_requests](symbols/hyperproc.archive.dlr._requests.md) — internal
- [credentials](symbols/hyperproc.archive.dlr.credentials.md)
- [_page_says](symbols/hyperproc.archive.dlr._page_says.md) — internal
- [_post_to](symbols/hyperproc.archive.dlr._post_to.md) — internal
- [sign_in](symbols/hyperproc.archive.dlr.sign_in.md)
- [read_policy](symbols/hyperproc.archive.dlr.read_policy.md)
- [_visible_text](symbols/hyperproc.archive.dlr._visible_text.md) — internal
- [_rfc3339](symbols/hyperproc.archive.dlr._rfc3339.md) — internal
- [_time_of](symbols/hyperproc.archive.dlr._time_of.md) — internal
- [_links](symbols/hyperproc.archive.dlr._links.md) — internal
- [search](symbols/hyperproc.archive.dlr.search.md)
- [_granule](symbols/hyperproc.archive.dlr._granule.md) — internal
- [_content_range](symbols/hyperproc.archive.dlr._content_range.md) — internal
- [_retryable](symbols/hyperproc.archive.dlr._retryable.md) — internal
- [_stream](symbols/hyperproc.archive.dlr._stream.md) — internal
- [download](symbols/hyperproc.archive.dlr.download.md)
- [_Forms](symbols/hyperproc.archive.dlr._Forms.md)

## Constant expressions

- [BASE](constants/hyperproc.archive.dlr.BASE.md)
- [RETRIES](constants/hyperproc.archive.dlr.RETRIES.md)
- [BACKOFF_S](constants/hyperproc.archive.dlr.BACKOFF_S.md)
- [SIGNUP](constants/hyperproc.archive.dlr.SIGNUP.md)
- [SSO](constants/hyperproc.archive.dlr.SSO.md)
- [NEEDS_LOGIN](constants/hyperproc.archive.dlr.NEEDS_LOGIN.md)
- [PAGE](constants/hyperproc.archive.dlr.PAGE.md)
- [_FRACTION](constants/hyperproc.archive.dlr._FRACTION.md)
- [READER_FILES](constants/hyperproc.archive.dlr.READER_FILES.md)
- [POLICY_WORDS](constants/hyperproc.archive.dlr.POLICY_WORDS.md)
