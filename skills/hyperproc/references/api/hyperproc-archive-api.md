# hyperproc.archive.api

Release baseline **0.1.2**; source `hyperproc/archive/api.py`. Choose a callable below rather than loading every declaration.

One ``search`` and one ``download`` over three archives.

The backend is decided by what you asked for, not by which function you called:
:func:`hyperproc.search` looks the ``(sensor, level)`` pair up in
:data:`hyperproc.archive.COLLECTIONS` and hands the query to CMR, NEON or DLR.
The three return the same :class:`~hyperproc.archive.results.Granule`, so the
rest of a workflow does not care which answered.

## Imported aliases

- `cmr` → `hyperproc.archive.cmr`
- `dlr` → `hyperproc.archive.dlr`
- `neon` → `hyperproc.archive.neon`
- `BACKENDS` → `hyperproc.archive.collections.BACKENDS`
- `resolve` → `hyperproc.archive.collections.resolve`
- `Granule` → `hyperproc.archive.results.Granule`
- `Results` → `hyperproc.archive.results.Results`

## Declared callables and classes

- [search](symbols/hyperproc.archive.api.search.md)
- [download](symbols/hyperproc.archive.api.download.md)
- [credentials](symbols/hyperproc.archive.api.credentials.md)
- [can_download](symbols/hyperproc.archive.api.can_download.md)
- [files](symbols/hyperproc.archive.api.files.md)

## Constant expressions

- [_BACKEND](constants/hyperproc.archive.api._BACKEND.md)
- [_DOWNLOAD_ARGS](constants/hyperproc.archive.api._DOWNLOAD_ARGS.md)
