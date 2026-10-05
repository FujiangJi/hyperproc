# hyperproc.archive.cmr.download

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def download(results, out_dir: str | Path='data', workers: int=8, verbose: bool=True) -> list[Path]
```

Fetch granules into ``out_dir``.

Args:
    results: a :class:`Results`, a list of :class:`Granule`, or one granule.
    out_dir: created if missing. Everything lands flat, which is what the
        readers expect - they find a granule's siblings by name.
    workers: parallel connections.

Returns:
    the downloaded paths.

Needs a free Earthdata login; ``earthaccess`` reads ``~/.netrc`` or the
``EARTHDATA_USERNAME``/``EARTHDATA_PASSWORD`` variables, else asks once.

[Module and aliases](../hyperproc-archive-cmr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.cmr.download --runtime`.
