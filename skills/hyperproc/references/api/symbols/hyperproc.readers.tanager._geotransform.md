# hyperproc.readers.tanager._geotransform

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _geotransform(h, ny: int, nx: int)
```

GDAL-order transform from the HDF-EOS StructMetadata text block.

``PixelRegistration=HE5_HDFE_CORNER`` with ``GridOrigin=HE5_HDFE_GD_UL``
means UpperLeftPointMtrs is the outer *edge* of the first pixel, not its
centre - so it is already the GDAL origin and needs no half-pixel shift.

[Module and aliases](../hyperproc-readers-tanager.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.tanager._geotransform --runtime`.
