# hyperproc.readers

Release baseline **0.1.2**; source `hyperproc/readers/__init__.py`. Choose a callable below rather than loading every declaration.

One module per sensor. Each exposes ``open_<sensor>(path, **kw) -> xr.Dataset``.

Import them from here or let :func:`hyperproc.open` dispatch for you.

## Declared exports

`check_geometry`, `fix_slope_convention`, `open_aviris`, `open_desis`, `open_emit`, `open_enmap`, `open_neon`, `open_pace`, `open_prisma`, `open_tanager`

## Imported aliases

- `check_geometry` → `hyperproc.readers.aviris.check_geometry`
- `fix_slope_convention` → `hyperproc.readers.aviris.fix_slope_convention`
- `open_aviris` → `hyperproc.readers.aviris.open_aviris`
- `open_desis` → `hyperproc.readers.desis.open_desis`
- `open_emit` → `hyperproc.readers.emit.open_emit`
- `open_enmap` → `hyperproc.readers.enmap.open_enmap`
- `open_neon` → `hyperproc.readers.neon.open_neon`
- `open_pace` → `hyperproc.readers.pace.open_pace`
- `open_prisma` → `hyperproc.readers.prisma.open_prisma`
- `open_tanager` → `hyperproc.readers.tanager.open_tanager`

## Declared callables and classes

