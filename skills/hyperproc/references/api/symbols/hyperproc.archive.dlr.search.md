# hyperproc.archive.dlr.search

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def search(sensor: str, level: str | None=None, *, bbox=None, date=None, cloud: tuple[float, float] | None=None, count: int=100, assets: str='reader', verbose: bool=True, **kwargs) -> Results
```

Find EnMAP or DESIS scenes in DLR's STAC catalogue.

Args:
    sensor: ``"ENMAP"`` or ``"DESIS"``.
    level: EnMAP ``"L1B"`` (unmerged detectors), ``"L1C"`` (orthorectified
        radiance) or ``"L2A"`` (surface reflectance); DESIS ``"L2A"``.
    bbox: ``(west, south, east, north)`` in degrees. **Give one.** The
        catalogue is large and a cloud filter without a box scans it all,
        which times out rather than answering.
    date: ``("YYYY-MM-DD", "YYYY-MM-DD")``, or a single day, which means
        that whole day.
    cloud: ``(min, max)`` percent, from the provider's ``eo:cloud_cover``.
    count: cap on scenes returned. ``-1`` for every match, paged.
    assets: which files each result links to. ``"reader"`` (default) is
        what :func:`hyperproc.open` uses - metadata, the spectral image and
        the quality masks. ``"image"`` drops the masks, ``"all"`` adds the
        browse images and thumbnails.
    verbose: print the query and the total.

Returns:
    :class:`Results`, newest first. DLR publishes no file sizes, so the
    totals read "size not published" rather than guessing.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr.search --runtime`.
