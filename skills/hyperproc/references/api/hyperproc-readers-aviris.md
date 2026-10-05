# hyperproc.readers.aviris

Release baseline **0.1.2**; source `hyperproc/readers/aviris.py`. Choose a callable below rather than loading every declaration.

AVIRIS reader - Classic, NG, 3 and 5, radiance and reflectance.

Four instruments in one JPL family, spanning thirty years and two file formats.
All four ship **orthorectified** cubes, so unlike EMIT or PACE there is no GLT
to apply to the image itself - the reader hands back a map-projected grid.

================  ==========================  =====  ===========================
instrument        granule id                  bands  cube
================  ==========================  =====  ===========================
AVIRIS-Classic    ``f201013t01p00r10``          224  ``*_sc01_ort_img``,
                                                     ``*_corr_*_img``  (ENVI)
AVIRIS-NG         ``ang20220224t210144``        425  ``*_rdn_*_img``,
                                                     ``*_rfl_*_img``   (ENVI)
AVIRIS-3          ``AV320231005t181518``        284  ``*_RDN_ORT``,
                                                     ``*_RFL_ORT``     (ENVI)
AVIRIS-5          ``AV520250508t173511_000``    424  ``*_RDN.nc``,
                                                     ``*_RFL_ORT.nc`` (NetCDF-4)
================  ==========================  =====  ===========================

Six things to know:

1. **The grids are flight-aligned, not north-up.** Every ENVI variant carries a
   ``rotation`` in its ``map info`` - -13 deg for the AVIRIS-3 line here, -50
   for the NG one, +29 for Classic - so the affine has non-zero shear terms and
   the 1-D ``x``/``y`` coordinates cannot describe it on their own.
   ``attrs["transform"]`` (GDAL order) is the authoritative georeferencing;
   pass ``map_coords=True`` for exact 2-D ``easting``/``northing``. AVIRIS-5 is
   the exception - it ships a north-up NetCDF grid.

2. **Classic radiance is scaled integers.** The cube is big-endian ``int16``
   and must be divided by the per-band factors in the ``.gain`` sidecar (300,
   600 or 1200 here) to reach uW nm-1 cm-2 sr-1. NG and AVIRIS-3 store float
   radiance in those units already. Reflectance is unitless 0-1 everywhere.

3. **Geometry lives in a separate file, often a separate directory.** The OBS
   cube carries path length, view and solar angles, slope, aspect and
   ``cos_i`` - everything topographic and BRDF correction needs. For NG and
   Classic the reflectance and radiance ship as two sibling folders and only
   the radiance one holds the OBS, so the reader searches sibling directories
   for the same granule id.

4. **AVIRIS-5's two levels are not on the same grid.** Its L2A reflectance is
   orthorectified, but its OBS *and* its L1B radiance are raw ``(line,
   sample)`` and ship their own lookup table, so the reader applies that GLT to
   bring them onto the reflectance grid. The other three deliver ``*_obs_ort``
   and ortho cubes throughout. Note the radiance is a separate ORNL DAAC
   collection (``AV5_L1B_RDN``) from the L2A bundle, so a folder holding only
   L2A products genuinely has no radiance in it.

5. **AVIRIS-3's slope and cos_i are wrong as delivered.** Slope is stored from
   *vertical*, and ``cos_i`` is computed from that, which leaves both unusable
   for topographic correction. This is not assumed per instrument: every
   variant ships a DEM, so :func:`check_geometry` differentiates it and decides
   from the correlation, and :func:`fix_slope_convention` rebuilds the pair
   when the verdict says so. ``fix_geometry=False`` returns the file untouched.

6. **No-data is not -9999 everywhere.** Classic radiance declares none in its
   header and fills off-swath cells with -50, which survives the gain division
   as -0.167 and drags a scene median negative if it is not masked.

Cubes here run 10-30 GB, so they are opened lazily through dask; nothing is
read until you slice or compute. ``wl_range`` subsets bands before any read.

## Imported aliases

- `crs_text` → `hyperproc.readers._common.crs_text`
- `datetime_from_id` → `hyperproc.readers._common.datetime_from_id`
- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`
- `check_geometry` → `hyperproc.geometry.check_geometry`
- `fix_slope_convention` → `hyperproc.geometry.fix_slope_convention`

## Declared callables and classes

- [open_aviris](symbols/hyperproc.readers.aviris.open_aviris.md)
- [_identify](symbols/hyperproc.readers.aviris._identify.md) — internal
- [_find_cube](symbols/hyperproc.readers.aviris._find_cube.md) — internal
- [_guess_product](symbols/hyperproc.readers.aviris._guess_product.md) — internal
- [_search](symbols/hyperproc.readers.aviris._search.md) — internal
- [_sibling](symbols/hyperproc.readers.aviris._sibling.md) — internal
- [read_hdr](symbols/hyperproc.readers.aviris.read_hdr.md)
- [_good_bands](symbols/hyperproc.readers.aviris._good_bands.md) — internal
- [_fill_value](symbols/hyperproc.readers.aviris._fill_value.md) — internal
- [_hdr_array](symbols/hyperproc.readers.aviris._hdr_array.md) — internal
- [_chunks_for](symbols/hyperproc.readers.aviris._chunks_for.md) — internal
- [_open_envi](symbols/hyperproc.readers.aviris._open_envi.md) — internal
- [_hdr_for](symbols/hyperproc.readers.aviris._hdr_for.md) — internal
- [_rotation](symbols/hyperproc.readers.aviris._rotation.md) — internal
- [_read_spc](symbols/hyperproc.readers.aviris._read_spc.md) — internal
- [_gain](symbols/hyperproc.readers.aviris._gain.md) — internal
- [_band_subset](symbols/hyperproc.readers.aviris._band_subset.md) — internal
- [_open_av5](symbols/hyperproc.readers.aviris._open_av5.md) — internal
- [_gather](symbols/hyperproc.readers.aviris._gather.md) — internal
- [_glt_cube](symbols/hyperproc.readers.aviris._glt_cube.md) — internal
- [_av5_cube_group](symbols/hyperproc.readers.aviris._av5_cube_group.md) — internal
- [_av5_grid](symbols/hyperproc.readers.aviris._av5_grid.md) — internal
- [_as_str](symbols/hyperproc.readers.aviris._as_str.md) — internal
- [_apply_glt](symbols/hyperproc.readers.aviris._apply_glt.md) — internal
- [_finish](symbols/hyperproc.readers.aviris._finish.md) — internal
- [_add_map_coords](symbols/hyperproc.readers.aviris._add_map_coords.md) — internal
- [_blank_water_bands](symbols/hyperproc.readers.aviris._blank_water_bands.md) — internal
- [_add_geometry](symbols/hyperproc.readers.aviris._add_geometry.md) — internal
- [_add_geometry_envi](symbols/hyperproc.readers.aviris._add_geometry_envi.md) — internal
- [_add_geometry_av5](symbols/hyperproc.readers.aviris._add_geometry_av5.md) — internal
- [_elevation_array](symbols/hyperproc.readers.aviris._elevation_array.md) — internal
- [_add_elevation](symbols/hyperproc.readers.aviris._add_elevation.md) — internal
- [_add_extras](symbols/hyperproc.readers.aviris._add_extras.md) — internal
- [_add_uncertainty](symbols/hyperproc.readers.aviris._add_uncertainty.md) — internal
- [_Variant](symbols/hyperproc.readers.aviris._Variant.md)

## Constant expressions

- [FILL](constants/hyperproc.readers.aviris.FILL.md)
- [CLASSIC_RDN_FILL](constants/hyperproc.readers.aviris.CLASSIC_RDN_FILL.md)
- [WATER_BANDS](constants/hyperproc.readers.aviris.WATER_BANDS.md)
- [OBS_BANDS](constants/hyperproc.readers.aviris.OBS_BANDS.md)
- [OBS_UNITS](constants/hyperproc.readers.aviris.OBS_UNITS.md)
- [AV5_OBS](constants/hyperproc.readers.aviris.AV5_OBS.md)
- [ELEVATION](constants/hyperproc.readers.aviris.ELEVATION.md)
- [TOPO_LAYERS](constants/hyperproc.readers.aviris.TOPO_LAYERS.md)
- [VARIANTS](constants/hyperproc.readers.aviris.VARIANTS.md)
