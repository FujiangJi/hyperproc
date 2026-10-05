# hyperproc.correct.mcd43.Params

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

A window of MCD43A1 parameters on a geographic grid.

Attributes:
    values: ``(ny, nx, 7, 3)`` float32 in reflectance units, NaN where the
        product has no retrieval. The last axis is ``iso, vol, geo``.
    transform: affine of the grid, ``(a, b, c, d, e, f)`` as
        ``x = c + a*col``, ``y = f + e*row`` (pixel corners).
    crs: always ``"EPSG:4326"`` for a downloaded stack.
    date: the acquisition date actually used, ``YYYY-MM-DD``.
    quality: ``(ny, nx, 7)`` uint8 band quality (0 best full inversion,
        1 full inversion, 2-3 magnitude inversion, 255 fill) or None.
    snow: ``(ny, nx)`` uint8 snow flag (0 snow-free, 1 snow, 255 fill) or None.

## Declared fields

```text
values: np.ndarray
transform: tuple
crs: str = 'EPSG:4326'
date: str = ''
quality: np.ndarray | None = None
snow: np.ndarray | None = None
path: Path | None = None
attrs: dict = field(default_factory=dict)
```

## Declared members

- [shape](hyperproc.correct.mcd43.Params.shape.md)
- [coverage](hyperproc.correct.mcd43.Params.coverage.md)
- [masked](hyperproc.correct.mcd43.Params.masked.md)
- [rowcol](hyperproc.correct.mcd43.Params.rowcol.md)
- [sample](hyperproc.correct.mcd43.Params.sample.md)
- [to_geotiff](hyperproc.correct.mcd43.Params.to_geotiff.md)

[Module](../hyperproc-correct-mcd43.md).
