# hyperproc.readers.neon

Release baseline **0.1.2**; source `hyperproc/readers/neon.py`. Choose a callable below rather than loading every declaration.

NEON AOP reader - DP1.30006.001 flightline reflectance (NIS), HDF5.

NEON's Airborne Observation Platform flies the NEON Imaging Spectrometer
(an AVIRIS-NG-class instrument) over its ecological sites and delivers
orthorectified, atmospherically corrected (ATCOR) reflectance as one HDF5 file
per flightline, on a north-up 1 m UTM grid:

    NEON_D01_BART_DP1_20190825_145110_reflectance.h5
         ^   ^    ^   ^        ^
      domain site product date  flightline start (HHMMSS)

Everything lives under one site group - ``<SITE>/Reflectance/`` - with the
cube in ``Reflectance_Data`` as ``(line, sample, wavelength)`` int16 scaled by
10 000, and a rich ``Metadata/`` tree: 426 band centres and FWHM, the map
projection, per-pixel view angles, scalar solar angles for the line, and the
ATCOR inputs and outputs (slope, aspect, smoothed DEM, illumination, path
length, sky view, AOT, water vapour, haze/cloud/water and DDV class maps).

Five things to know, all checked against the BART 2019-08-25 lines here:

1. **The cube is already ``(y, x, wavelength)``.** No transpose, no GLT: NEON
   delivers a gridded product. The ``Interleave = BSQ`` attribute describes
   the *conceptual* layout, not the array order in the file.

2. **Some attribute labels are wrong, so values were checked, not trusted.**
   ``Smooth_Surface_Elevation`` is labelled "Average Solar Zenith Angle" in
   degrees; it holds elevation in metres (680-735 m at Bartlett).
   ``Illumination_Factor`` is labelled degrees; it is ``cos(i) x 100`` as
   uint8 - ``IF/100`` matches the incidence formula from slope, aspect and the
   solar angles at r = +0.9994, mean |diff| 0.0025, while cos(IF deg) is
   anti-correlated. ``Water_Vapor_Column`` has ``Scale_Factor = 1.0`` but its
   description says "[cm] x 1000", and 816 cm of water vapour is impossible
   where 0.816 cm is August in New Hampshire. The reader applies the scale the
   values demand and records each decision in the variable's ``note``.

3. **``Cast_Shadow`` does not hold the flag its description promises.** It
   documents ``1 = shadow, 0 = no shadow``; the line here holds only 1 and
   241, with 241 on the off-swath fill. It is exposed unmodified as
   ``cast_shadow_raw`` rather than given a meaning the data do not support.
   Use the ``hcw_class`` and ``ddv_class`` maps for shadow instead - both
   carry an explicit topographic-shadow class.

4. **Solar angles are one number per flightline**, not per pixel: ATCOR uses
   the line average. They are broadcast to ``(y, x)`` lazily so downstream code
   sees the same variables as for AVIRIS, and kept as scalar attrs too.

5. **Bad bands are the provider's.** ``Band_Window_1/2_Nanometers`` on the
   Reflectance group give NEON's own water-vapour windows (1340-1445 and
   1790-1955 nm here), and ``good_wavelength`` is built from them.

The cube is opened lazily through dask, chunked to the file's own gzip layout
``(336, 39, 14)`` in multiples, so a spatial window across all bands is a
handful of contiguous reads rather than a pass over 5 GB.

## Imported aliases

- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`
- `check_geometry` → `hyperproc.geometry.check_geometry`
- `fix_slope_convention` → `hyperproc.geometry.fix_slope_convention`

## Declared callables and classes

- [open_neon](symbols/hyperproc.readers.neon.open_neon.md)
- [_as_str](symbols/hyperproc.readers.neon._as_str.md) — internal
- [_band_subset](symbols/hyperproc.readers.neon._band_subset.md) — internal
- [_good_bands](symbols/hyperproc.readers.neon._good_bands.md) — internal
- [_grid](symbols/hyperproc.readers.neon._grid.md) — internal
- [_chunks_for](symbols/hyperproc.readers.neon._chunks_for.md) — internal
- [_lazy_cube](symbols/hyperproc.readers.neon._lazy_cube.md) — internal
- [_lazy_layer](symbols/hyperproc.readers.neon._lazy_layer.md) — internal
- [_scaled](symbols/hyperproc.readers.neon._scaled.md) — internal
- [_add_layers](symbols/hyperproc.readers.neon._add_layers.md) — internal
- [_add_geometry](symbols/hyperproc.readers.neon._add_geometry.md) — internal
- [_add_classes](symbols/hyperproc.readers.neon._add_classes.md) — internal
- [_H5Array](symbols/hyperproc.readers.neon._H5Array.md)

## Constant expressions

- [FILL](constants/hyperproc.readers.neon.FILL.md)
- [SCALE](constants/hyperproc.readers.neon.SCALE.md)
- [_GRANULE](constants/hyperproc.readers.neon._GRANULE.md)
- [ANCILLARY](constants/hyperproc.readers.neon.ANCILLARY.md)
- [BYTE_NODATA](constants/hyperproc.readers.neon.BYTE_NODATA.md)
- [CLASSES](constants/hyperproc.readers.neon.CLASSES.md)
- [NOTES](constants/hyperproc.readers.neon.NOTES.md)
