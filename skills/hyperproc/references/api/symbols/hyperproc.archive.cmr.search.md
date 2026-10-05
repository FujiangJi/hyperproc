# hyperproc.archive.cmr.search

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def search(sensor: str, level: str | None=None, *, bbox=None, date=None, cloud: tuple[float, float] | None=None, version: str | None=None, count: int=100, verbose: bool=True, **kwargs) -> Results
```

Find granules.

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

[Module and aliases](../hyperproc-archive-cmr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.cmr.search --runtime`.
