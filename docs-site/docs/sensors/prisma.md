# PRISMA

PRISMA support covers four product levels with different meanings:

| Level | Quantity | Spatial representation |
|---|---|---|
| L1 | At-sensor radiance | Swath |
| L2B | At-surface radiance | Geolocated swath |
| L2C | Surface reflectance | Geolocated swath |
| L2D | Surface reflectance | Mapped grid |

```python
ds = hp.open("/path/to/PRS_L2D_STD_product.he5", join_priority="swir")
```

## Detector handling

The reader reorganizes HDF-EOS detector arrays, removes zero-wavelength entries, orders wavelengths, and handles VNIR/SWIR overlap. `cube="vnir"`, `"swir"`, or `"full"` selects detector coverage. `join_priority` controls which detector contributes in the overlap; the default is SWIR. Keep this decision in any comparison near the join.

Provider scaling differs by level. L1 radiance is represented in W m⁻² sr⁻¹ µm⁻¹; L2 reflectance is dimensionless after its level-specific conversion. Do not apply a single scaling formula to all levels.

## Geometry and quality

For L1, geometry/geolocation can be borrowed from suitable L2 siblings, with other fallback paths documented in the reader. That dependency should be recorded. Elevation may need to be supplied separately. Optional error matrices and retrieval maps are not interchangeable with a provider good-band list.

`good_bands_only=True` is not a general PRISMA quality switch; the reader rejects that request when no provider good-band flag exists. L2D padding also requires attention.

## Analysis

Georeference a swath before regular raster export. The spline gap-filling defaults are PRISMA-oriented but remain an optional spectral modification, with interpolation flags—not an automatic mandatory step.

[Reader API](../api/hyperproc-readers-prisma.md) · [Window tutorial](../tutorials/prisma-window-tutorial.md)
