# hyperproc.correct.mcd43.fetch

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fetch(bounds=None, date: str | None=None, out_dir=None, *, ds=None, source: str='gee', res: float | None=None, pad: float=0.05, days: int=8, quality: bool=True, project: str | None=None, overwrite: bool=False, tile: int=TILE, verbose: bool=True) -> Params
```

MCD43A1 parameters covering ``bounds`` on ``date``, downloaded once and cached.

Args:
    bounds: ``(w, s, e, n)`` in degrees. Taken from ``ds`` when omitted.
    date: ``YYYY-MM-DD``. Taken from ``ds`` when omitted.
    out_dir: where the GeoTIFF goes; default ``$HYPERPROC_CACHE_DIR/mcd43``.
    ds: a hyperproc dataset to read the footprint and date from.
    source: ``"gee"`` to download, ``"local"`` to only use the cache.
    res: grid step in degrees. The default None adapts to ``ds``: the
        product's native 1/240 degree for any image finer than that, and a
        whole multiple of it, with the MODIS cells averaged, for an image
        coarser than that. Pass a number to pin it.
    pad: degrees added around the footprint so bilinear sampling has
        neighbours at the edge.
    days: how far to look for a granule if the exact date is missing.
    quality: also fetch the MCD43A2 per-band quality and snow flags.
    project: Earth Engine Cloud project.
    overwrite: re-download even if the cached file exists.

Returns:
    :class:`Params`.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.fetch --runtime`.
