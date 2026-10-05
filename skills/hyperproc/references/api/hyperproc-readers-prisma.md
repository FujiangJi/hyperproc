# hyperproc.readers.prisma

Release baseline **0.1.2**; source `hyperproc/readers/prisma.py`. Choose a callable below rather than loading every declaration.

PRISMA (ASI) reader for L1 / L2B / L2C / L2D HDF-EOS5 granules.

A Python port of the parts of `prismaread <https://github.com/irea-cnr-mi/prismaread>`_
(``pr_convert``) that matter for analysis. Four things about the format catch
people out, and this module handles all of them:

1. **Cubes are stored band-interleaved**, shaped ``(rows, bands, cols)``, not
   ``(rows, cols, bands)``. Reading them naively transposes your image.
2. **Wavelengths run descending** in both spectrometers - the first VNIR band
   is ~977 nm, the last ~407 nm. They are flipped to ascending here.
3. **Some bands are not acquired at all** and carry a centre wavelength of
   exactly ``0.0``, flagged in ``List_Cw_*_Flags``. On this granule that is
   3 VNIR and 2 SWIR bands. They are dropped - a 0 nm band is not data.
4. **VNIR and SWIR overlap** around 943-977 nm. ``join_priority`` decides which
   spectrometer wins there, matching prismaread's argument of the same name.

DN are stored as ``uint16`` and rescaled per spectrometer. L2 uses a min/max
stretch, L1 a factor and offset::

    L2:  value = ScaleMin + DN * (ScaleMax - ScaleMin) / 65535
    L1:  value = DN / ScaleFactor - Offset            (W m-2 sr-1 um-1)

L1 ships no per-pixel angles and no elevation. When the L2C (or L2B) file of
the same acquisition sits beside it, its ``Geometric Fields`` and its refined
geolocation are borrowed (``angles_source="l2"``, the default); otherwise the
view angles are computed from the satellite ephemeris in the file and the sun
angles are the scene-level values. Elevation is left to
:func:`hyperproc.atmos.dem.add_elevation`.

Levels differ in geometry, not in cube layout:

=======  ===================================  ==========================
level    grid                                 georeferencing
=======  ===================================  ==========================
L1       1000 x 1000 swath, TOA radiance      lat/lon arrays
L2B      1000 x 1000 swath, surface radiance  lat/lon arrays
L2C      1000 x 1000 swath, reflectance       lat/lon arrays
L2D      n x m UTM grid, reflectance          EPSG + affine transform
=======  ===================================  ==========================

## Imported aliases

- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`

## Declared callables and classes

- [open_prisma](symbols/hyperproc.readers.prisma.open_prisma.md)
- [_read_arm](symbols/hyperproc.readers.prisma._read_arm.md) — internal
- [_take](symbols/hyperproc.readers.prisma._take.md) — internal
- [_resolve_overlap](symbols/hyperproc.readers.prisma._resolve_overlap.md) — internal
- [_dec](symbols/hyperproc.readers.prisma._dec.md) — internal
- [_scene_attrs](symbols/hyperproc.readers.prisma._scene_attrs.md) — internal
- [_fill_mask](symbols/hyperproc.readers.prisma._fill_mask.md) — internal
- [_add_grid](symbols/hyperproc.readers.prisma._add_grid.md) — internal
- [_add_angles](symbols/hyperproc.readers.prisma._add_angles.md) — internal
- [_add_l1_masks](symbols/hyperproc.readers.prisma._add_l1_masks.md) — internal
- [_l2_sibling](symbols/hyperproc.readers.prisma._l2_sibling.md) — internal
- [_borrow_geolocation](symbols/hyperproc.readers.prisma._borrow_geolocation.md) — internal
- [_add_l1_geometry](symbols/hyperproc.readers.prisma._add_l1_geometry.md) — internal
- [_view_from_ephemeris](symbols/hyperproc.readers.prisma._view_from_ephemeris.md) — internal
- [_add_l2c_maps](symbols/hyperproc.readers.prisma._add_l2c_maps.md) — internal

## Constant expressions

- [DN_MAX](constants/hyperproc.readers.prisma.DN_MAX.md)
- [LEVEL_SPEC](constants/hyperproc.readers.prisma.LEVEL_SPEC.md)
- [ANGLE_FIELDS](constants/hyperproc.readers.prisma.ANGLE_FIELDS.md)
- [L2C_MAPS](constants/hyperproc.readers.prisma.L2C_MAPS.md)
- [_GRANULE](constants/hyperproc.readers.prisma._GRANULE.md)
- [L1_MASKS](constants/hyperproc.readers.prisma.L1_MASKS.md)
