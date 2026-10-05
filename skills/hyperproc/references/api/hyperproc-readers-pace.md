# hyperproc.readers.pace

Release baseline **0.1.2**; source `hyperproc/readers/pace.py`. Choose a callable below rather than loading every declaration.

PACE OCI (NASA) reader for L1B and L2 SFREFL granules.

OCI is a very different instrument from the land imagers in this package: a
~1 km ocean-colour spectrometer on a wide swath. One granule here covers 25 to
49 degrees north and 119 to 84 degrees west - most of the continental US - so it
is a *global-scale* product, not a scene.

=======  ==========================  ==================  ===================
level    variable                    bands               geometry
=======  ==========================  ==================  ===================
L1B      ``rhot`` TOA reflectance    291 (blue+red+SWIR) full, in-file
L2       ``rhos`` surface reflectance 122                none - from L1B
=======  ==========================  ==================  ===================

Three things catch people out:

1. **L1B splits the detector into three arrays** - ``rhot_blue`` (119 bands,
   315-606 nm), ``rhot_red`` (163, 600-895 nm) and ``rhot_SWIR`` (9, 940-2258
   nm), which overlap slightly. They are read, concatenated and sorted here.
2. **L1B stores bands first**, ``(band, scan, pixel)``, not last. Reading it
   naively transposes the image.
3. **L2 carries *some* geometry.** ``scan_line_attributes/csol_z`` gives a
   per-scan-line centre solar zenith and ``navigation_data/tilt`` the OCI tilt
   (used to dodge sunglint); both are read here and broadcast across track. The
   full per-pixel ``saa``/``vza``/``vaa`` live only in the L1B granule for the
   same timestamp, which is located automatically when it sits alongside.
4. **Neither level ships FWHM.** The 5 nm hyperspectral sampling is used as a
   documented nominal; the SWIR bands get their real bandpass, which runs
   15-80 nm and is nothing like 5.

Both levels are swaths with per-pixel lat/lon and no CRS. Use
:func:`hyperproc.georeference` to put them on a grid; it defaults to EPSG:4326
here rather than a UTM zone, because the swath is far too wide for one.

## Imported aliases

- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`

## Declared callables and classes

- [open_pace](symbols/hyperproc.readers.pace.open_pace.md)
- [_fwhm_for](symbols/hyperproc.readers.pace._fwhm_for.md) — internal
- [_read_l2](symbols/hyperproc.readers.pace._read_l2.md) — internal
- [_read_l1b](symbols/hyperproc.readers.pace._read_l1b.md) — internal
- [_add_latlon](symbols/hyperproc.readers.pace._add_latlon.md) — internal
- [_add_flags](symbols/hyperproc.readers.pace._add_flags.md) — internal
- [_add_scanline](symbols/hyperproc.readers.pace._add_scanline.md) — internal
- [_add_geometry](symbols/hyperproc.readers.pace._add_geometry.md) — internal

## Constant expressions

- [FILL](constants/hyperproc.readers.pace.FILL.md)
- [NOMINAL_FWHM_NM](constants/hyperproc.readers.pace.NOMINAL_FWHM_NM.md)
- [SWIR_BANDPASS](constants/hyperproc.readers.pace.SWIR_BANDPASS.md)
- [ARMS](constants/hyperproc.readers.pace.ARMS.md)
- [FLAGS](constants/hyperproc.readers.pace.FLAGS.md)
- [GEOM](constants/hyperproc.readers.pace.GEOM.md)
- [_GRANULE](constants/hyperproc.readers.pace._GRANULE.md)
