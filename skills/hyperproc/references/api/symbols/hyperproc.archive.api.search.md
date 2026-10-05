# hyperproc.archive.api.search

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def search(sensor: str, level: str | None=None, **kwargs) -> Results
```

Find granules in whichever archive publishes them.

Args:
    sensor: ``"EMIT"``, ``"PACE"``, ``"AVIRIS-3"``, ``"AVIRIS-5"``,
        ``"NEON"``, ``"ENMAP"``, ``"DESIS"``. The reader spellings work too
        (``"aviris3"``, ``"oci"``).
    level: ``"L1B"``/``"L1"`` for radiance, ``"L2A"``/``"L2"`` for
        reflectance. Required where a sensor has more than one searchable
        level. :func:`describe` prints the table.
    bbox: ``(west, south, east, north)`` in degrees.
    date: ``("YYYY-MM-DD", "YYYY-MM-DD")``, or a single date. NEON
        deliveries are monthly, so dates there are truncated to the month.
    cloud: ``(min, max)`` percent, where the provider reports it - EMIT,
        PACE, EnMAP and DESIS do; the AVIRIS collections and NEON do not.
    count: cap on results, default 100. ``-1`` for every match.
    verbose: print the query and the total.

Backend-specific arguments are accepted too and documented on the backend:
``version=`` (CMR), ``site=`` and ``site_radius_km=`` (NEON), ``assets=``
(DLR).

Returns:
    :class:`~hyperproc.archive.results.Results`.

Raises:
    ValueError: for a sensor no archive here carries, with the address of
        the archive that does.

[Module and aliases](../hyperproc-archive-api.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.api.search --runtime`.
