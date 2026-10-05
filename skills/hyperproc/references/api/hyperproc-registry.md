# hyperproc.registry

Release baseline **0.1.2**; source `hyperproc/registry.py`. Choose a callable below rather than loading every declaration.

Which reader handles which (sensor, level), and how to guess from a filename.

One table, one place to edit. Adding a sensor means writing its reader module
and flipping its ``loader`` entry here from ``None`` to the function.

## Declared callables and classes

- [_tanager](symbols/hyperproc.registry._tanager.md) — internal
- [_pace](symbols/hyperproc.registry._pace.md) — internal
- [_enmap](symbols/hyperproc.registry._enmap.md) — internal
- [_desis](symbols/hyperproc.registry._desis.md) — internal
- [_neon](symbols/hyperproc.registry._neon.md) — internal
- [_aviris](symbols/hyperproc.registry._aviris.md) — internal
- [_prisma](symbols/hyperproc.registry._prisma.md) — internal
- [_emit](symbols/hyperproc.registry._emit.md) — internal
- [register](symbols/hyperproc.registry.register.md)
- [sniff](symbols/hyperproc.registry.sniff.md)
- [resolve](symbols/hyperproc.registry.resolve.md)
- [summary](symbols/hyperproc.registry.summary.md)
- [list_readers](symbols/hyperproc.registry.list_readers.md)
- [Entry](symbols/hyperproc.registry.Entry.md)

## Constant expressions

- [REGISTRY](constants/hyperproc.registry.REGISTRY.md)
