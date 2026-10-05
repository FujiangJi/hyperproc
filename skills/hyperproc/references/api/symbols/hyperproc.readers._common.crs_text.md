# hyperproc.readers._common.crs_text

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def crs_text(crs) -> str | None
```

One spelling for ``attrs["crs"]``: ``"EPSG:<code>"`` when the CRS has an
EPSG code, WKT otherwise, ``None`` when there is no CRS at all.

Readers get their CRS from very different places (rasterio objects, ENVI
map info, netCDF ``spatial_ref`` WKT, integer EPSG attributes). Writing them
all through this keeps the attribute comparable across sensors and stops
``str(None)`` from turning into the literal text ``"None"``, which the
GeoTIFF writer would then try to use as a projection.

[Module and aliases](../hyperproc-readers-_common.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers._common.crs_text --runtime`.
