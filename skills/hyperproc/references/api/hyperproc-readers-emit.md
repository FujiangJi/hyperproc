# hyperproc.readers.emit

Release baseline **0.1.2**; source `hyperproc/readers/emit.py`. Choose a callable below rather than loading every declaration.

EMIT (NASA JPL, aboard the ISS) reader.

EMIT ships each granule as NetCDF-4 with three groups that xarray will not open
together, on a *sensor* grid (downtrack x crosstrack) rather than a map grid.
The ``location`` group carries a GLT (geometry lookup table) that maps it onto
the ortho grid, so orthorectification here is an index lookup, not a resample.

Two products are supported, and they share almost everything:

===========  =====  ==================  ====================
file         level  variable            units
===========  =====  ==================  ====================
``*_RFL_*``  L2A    ``reflectance``     unitless (0-1)
``*_RAD_*``  L1B    ``radiance``        uW/cm^2/SR/nm
===========  =====  ==================  ====================

The ``L2A_MASK`` and ``L1B_OBS`` siblings are picked up automatically for both,
since they describe the same scene. Needs only numpy + xarray.

## Imported aliases

- `crs_text` → `hyperproc.readers._common.crs_text`
- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`
- `_glt_cube` → `hyperproc.readers.aviris._glt_cube`

## Declared callables and classes

- [open_emit](symbols/hyperproc.readers.emit.open_emit.md)
- [_sibling](symbols/hyperproc.readers.emit._sibling.md) — internal
- [_add_masks](symbols/hyperproc.readers.emit._add_masks.md) — internal
- [_add_geometry](symbols/hyperproc.readers.emit._add_geometry.md) — internal
- [_stack_glt](symbols/hyperproc.readers.emit._stack_glt.md) — internal
- [_apply_glt](symbols/hyperproc.readers.emit._apply_glt.md) — internal

## Constant expressions

- [GLT_NODATA](constants/hyperproc.readers.emit.GLT_NODATA.md)
- [FILL_VALUE](constants/hyperproc.readers.emit.FILL_VALUE.md)
- [PRODUCTS](constants/hyperproc.readers.emit.PRODUCTS.md)
- [MASK_FLAGS](constants/hyperproc.readers.emit.MASK_FLAGS.md)
- [MASK_VALUES](constants/hyperproc.readers.emit.MASK_VALUES.md)
- [OBS_BANDS](constants/hyperproc.readers.emit.OBS_BANDS.md)
- [_GRANULE](constants/hyperproc.readers.emit._GRANULE.md)
