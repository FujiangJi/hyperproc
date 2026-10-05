# hyperproc.io.export_geometry

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def export_geometry(ds: xr.Dataset, path: str | Path, layers: tuple[str, ...] | None=None, overviews: bool | list[int] | None=None, overview_resampling: str='average') -> list[Path]
```

Write the geometry layers a topographic correction needs, one GeoTIFF each.

Saves looping :func:`to_geotiff_2d` by hand and, more to the point, saves
guessing which layers matter: :data:`GEOMETRY_LAYERS` is the set SCS+C, the
C-correction and a BRDF fit actually read - slope and aspect for the facet,
``cos_i`` for the illumination, the four angles for the kernels, elevation
and path length for the atmosphere.

Whatever the dataset does not carry is skipped rather than faked, so the
return value is the honest list of what exists for this granule.

Args:
    ds: dataset from :func:`hyperproc.open`, orthorectified.
    path: output directory. Files are named ``<granule>_<layer>.tif``.
    layers: override the default set.

Returns:
    The paths written, in the order attempted.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.export_geometry --runtime`.
