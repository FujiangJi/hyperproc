# hyperproc.readers.neon._grid

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _grid(meta, dset) -> tuple[int, tuple]
```

EPSG and GDAL-order transform from Map_Info, cross-checked to the extent.

Map_Info is ``proj, refx, refy, easting, northing, px, py, zone, hemi,
datum, units, rotation``; the easting/northing are the upper-left *edge*,
which the Spatial_Extent attribute confirms (extent width / px = samples).

[Module and aliases](../hyperproc-readers-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.neon._grid --runtime`.
