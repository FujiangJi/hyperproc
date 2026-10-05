# hyperproc.readers.enmap

Release baseline **0.1.2**; source `hyperproc/readers/enmap.py`. Choose a callable below rather than loading every declaration.

EnMAP (DLR/GFZ) reader for L1B / L1C / L2A GeoTIFF products.

224 bands, 418-2445 nm, 30 m, from a VNIR (91 bands) and a SWIR (133 bands)
spectrometer that overlap around 902-993 nm.

Three things differ from the other sensors here:

1. **L1B is two detectors on two grids, and stays that way here.** DLR ships
   ``SPECTRAL_IMAGE_VNIR`` and ``SPECTRAL_IMAGE_SWIR`` as separate files - and,
   tellingly, separate per-detector quality and pixel-mask products too - because
   at L1B the two focal planes have not been co-registered; that alignment is
   what the L1C geometric processing does. Stacking the two arrays by pixel
   index would produce a tidy 224-band cube whose spectra do not all come from
   the same ground spot, so the reader returns **one detector at a time** and
   refuses ``cube="full"`` on L1B. Both TIFs carry an identical EPSG:4326
   affine; it is a scene-level corner fit (about 34 x 32 m implied pixels), not a
   georeference, so it is kept as ``attrs["approx_geocoding_gdal"]`` and **not**
   as ``crs``/``transform`` - ``to_geotiff`` refuses an L1B cube, as it does
   for DESIS L1B. L1C and L2A ship one merged, co-registered 224-band file.
2. **Angles are given per scene corner**, not as a scalar or a raster. Viewing
   zenith runs 20.1 to 22.7 degrees across this scene, so the reader bilinearly
   interpolates the four corners into a real per-pixel grid. The corner values
   themselves stay in ``ds.attrs``.
3. **The sun angle is an elevation, not a zenith.** It is converted here
   (``sza = 90 - elevation``) so it matches every other reader.

Scaling is ``value = DN * GainOfBand + OffsetOfBand``. L2A uses a uniform gain
of 1e-4 with zero offset; **L1B and L1C carry a per-band gain and offset**.

## Imported aliases

- `crs_text` → `hyperproc.readers._common.crs_text`
- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`

## Declared callables and classes

- [_beside](symbols/hyperproc.readers.enmap._beside.md) — internal
- [open_enmap](symbols/hyperproc.readers.enmap.open_enmap.md)
- [_lazy_cube](symbols/hyperproc.readers.enmap._lazy_cube.md) — internal
- [_parse_metadata](symbols/hyperproc.readers.enmap._parse_metadata.md) — internal
- [_corner_grid](symbols/hyperproc.readers.enmap._corner_grid.md) — internal
- [_footprint_pixels](symbols/hyperproc.readers.enmap._footprint_pixels.md) — internal
- [_footprint_grid](symbols/hyperproc.readers.enmap._footprint_grid.md) — internal
- [_signed_area](symbols/hyperproc.readers.enmap._signed_area.md) — internal
- [_add_angles](symbols/hyperproc.readers.enmap._add_angles.md) — internal
- [_add_quality](symbols/hyperproc.readers.enmap._add_quality.md) — internal
- [_add_pixelmask](symbols/hyperproc.readers.enmap._add_pixelmask.md) — internal

## Constant expressions

- [LEVEL_SPEC](constants/hyperproc.readers.enmap.LEVEL_SPEC.md)
- [QUALITY_LAYERS](constants/hyperproc.readers.enmap.QUALITY_LAYERS.md)
- [ANGLE_TAGS](constants/hyperproc.readers.enmap.ANGLE_TAGS.md)
- [_CORNERS](constants/hyperproc.readers.enmap._CORNERS.md)
- [_GRANULE](constants/hyperproc.readers.enmap._GRANULE.md)
