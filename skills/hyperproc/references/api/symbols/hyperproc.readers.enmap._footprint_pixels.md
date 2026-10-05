# hyperproc.readers.enmap._footprint_pixels

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _footprint_pixels(root, crs, transform, ny: int, nx: int)
```

Pixel (col, row) of the four footprint corners, in _CORNERS order, or None.

The angle corners in the XML belong to the *footprint* (``boundingPolygon``
of ``spatialCoverage``), which on the north-up L1C/L2A raster is a rotated
quadrilateral inside the box, not the box's corners.

[Module and aliases](../hyperproc-readers-enmap.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.enmap._footprint_pixels --runtime`.
