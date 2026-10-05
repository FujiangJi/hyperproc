# hyperproc.archive.dlr.download

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def download(results, out_dir: str | Path='data', workers: int=4, user: str | None=None, password: str | None=None, accept_policy: bool=False, verbose: bool=True) -> list[Path]
```

Fetch EnMAP or DESIS files into ``out_dir``. Needs an EOC account.

Every file of a granule lands in the one directory, which is what the
readers expect: an EnMAP GeoTIFF carries no wavelengths of its own and
finds them in the ``METADATA.XML`` beside it.

A result set mixing EnMAP and DESIS is fine: each mission is fetched with
its own account if you have set one, since DLR grants access to the two
separately. See :func:`credentials`.

``accept_policy=True`` agrees to DLR's Acceptable Usage Policy from here;
without it, a pending policy stops the download and says where to read it.

A file whose connection breaks is resumed from the bytes already written,
where the server allows it, for as long as each connection adds some; it
gives up after :data:`RETRIES` breaks in a row that add nothing. Until it
is whole it sits beside its final name as ``*.part``, so a later call
carries on from it too, and a file shorter than the server announced is
never renamed into place.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr.download --runtime`.
