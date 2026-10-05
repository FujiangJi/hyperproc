# hyperproc.readers.enmap._beside

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _beside(path: Path, name: str) -> Path
```

The sibling ``name``, or DLR's cloud-optimised spelling of it.

The EOC Geoservice publishes every raster twice over: the plain GeoTIFF the
order form delivers, and a ``_COG`` copy, which is what the STAC catalogue
links and therefore what :func:`hyperproc.search` downloads. They hold the
same bands, so accepting both here means a searched granule opens without
anyone renaming files. Returns the plain name when neither exists, so the
caller's "missing" message names the file people expect.

[Module and aliases](../hyperproc-readers-enmap.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.enmap._beside --runtime`.
