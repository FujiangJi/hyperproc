# hyperproc.readers.tanager

Release baseline **0.1.2**; source `hyperproc/readers/tanager.py`. Choose a callable below rather than loading every declaration.

Tanager-1 (Planet / Carbon Mapper) reader for the orthorectified products.

Tanager-1 launched in August 2024: 426 bands, 376-2499 nm at 30 m, on a
free-flying smallsat. Planet distributes HDF-EOS5 **grids** rather than swaths,
so the products arrive already map-projected - no GLT, no resampling.

=================  ======  =========================  ====================
file                level   variable                   units
=================  ======  =========================  ====================
``*_ortho_sr_*``    L2A     ``reflectance``            unitless
``*_ortho_radiance_*`` L1B  ``radiance``               W/(m^2 sr um)
=================  ======  =========================  ====================

Three things to know:

1. **Cubes are band-first**, ``(band, y, x)``. Reading them naively transposes
   the image.
2. **Nothing lives in a sidecar** - wavelengths, FWHM, the good-band flag and
   the units are all HDF5 attributes on the cube dataset itself, and the grid
   geometry is in the HDF-EOS ``StructMetadata.0`` text block.
3. **The flagged bands are not a fill value.** 58 of the 426 bands are flagged,
   covering the water-vapour windows from 1342 to 1967 nm. About 76% of those
   values are exactly -0.01 and the rest are failed retrievals scattered from
   -0.24 to 1.38 - so unlike a NaN they all pass ``isfinite`` and read as data.
   ``good_bands_only=True`` blanks them while keeping the band count at 426, so
   indices stay aligned with the sensor's own grid. The radiance product ships
   no ``good_wavelengths`` attribute at all.

## Imported aliases

- `datetime_from_id` → `hyperproc.readers._common.datetime_from_id`
- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`

## Declared callables and classes

- [open_tanager](symbols/hyperproc.readers.tanager.open_tanager.md)
- [_lazy_cube](symbols/hyperproc.readers.tanager._lazy_cube.md) — internal
- [_geotransform](symbols/hyperproc.readers.tanager._geotransform.md) — internal
- [_add_masks](symbols/hyperproc.readers.tanager._add_masks.md) — internal
- [_add_geometry](symbols/hyperproc.readers.tanager._add_geometry.md) — internal

## Constant expressions

- [FILL](constants/hyperproc.readers.tanager.FILL.md)
- [GRID](constants/hyperproc.readers.tanager.GRID.md)
- [PRODUCTS](constants/hyperproc.readers.tanager.PRODUCTS.md)
- [GEOM](constants/hyperproc.readers.tanager.GEOM.md)
- [MASKS](constants/hyperproc.readers.tanager.MASKS.md)
- [EXTRAS](constants/hyperproc.readers.tanager.EXTRAS.md)
- [_GRANULE](constants/hyperproc.readers.tanager._GRANULE.md)
