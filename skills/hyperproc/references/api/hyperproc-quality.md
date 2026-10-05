# hyperproc.quality

Release baseline **0.1.2**; source `hyperproc/quality.py`. Choose a callable below rather than loading every declaration.

One quality layer for every sensor, as documented bit flags.

Each provider ships its own masks under its own names and its own polarity.
Nine spellings mean "cloud" across the readers in this package
(``cloud``, ``dilated_cloud``, ``cloud_land``, ``cloud_water``, ``cldice``,
and the cirrus variants); shadow is ``shadow`` on DESIS and ``cloudshadow`` on
EnMAP; ``valid`` is true when a pixel is good while ``nodata`` is true when it
is not; and the AVIRIS family ships nothing at all. Anyone who did not build
the pipeline has to learn all of that before they can mask a cube.

This module reduces it to one ``uint16`` layer with one bit per condition,
the way Landsat's ``QA_PIXEL`` does::

    import hyperproc as hp
    q = hp.quality_flags(ds)                # uint16 (y, x)
    hp.quality_summary(q)                   # {'cloud': 0.11, 'water': 0.38, ...}
    clear = hp.quality_apply(ds, q)         # cube set to NaN where cloudy or fill
    print(hp.quality_table(q))              # the bit table with per-flag shares

The per-sensor layers are left exactly as the readers produce them, so nothing
that already reads ``ds["cloud"]`` breaks; this is an additional view of them.

The bits
--------
=====  ====================  ===============================================
Bit    Flag                  Set when
=====  ====================  ===============================================
0      fill                  no observation (off-swath, nodata, nav failure)
1      saturated             a band is at the detector rail
2      cloud                 opaque cloud
3      cloud_shadow          shadow cast by cloud
4      cirrus                thin or high cloud
5      snow_ice              snow or ice
6      water                 inland or ocean water
7      haze                  aerosol haze flagged by the provider
8      sun_glint             specular reflection geometry
9      terrain_shadow        not illuminated by the direct beam (cos i <= 0)
10     steep_terrain         slope beyond what a topographic correction holds
11     ac_failed             atmospheric correction did not converge
12     brdf_filled           BRDF c-factor not taken from MODIS
13     negative_reflectance  many good bands below zero after correction
=====  ====================  ===============================================

Bits 14 and 15 are reserved. Stages add their own bits as they run:
:func:`hyperproc.correct.nbar` records ``brdf_filled`` through ``brdf_valid``,
and :func:`hyperproc.atmos.process` writes the layer beside every product.

## Declared exports

`FLAGS`, `FLAG_DESCRIPTIONS`, `BOOLEAN_SOURCES`, `CODED_SOURCES`, `DEFAULT_DROP`, `build`, `decode`, `summary`, `apply`, `set_flag`, `describe`

## Declared callables and classes

- [_bit](symbols/hyperproc.quality._bit.md) — internal
- [_as_2d](symbols/hyperproc.quality._as_2d.md) — internal
- [_band_nearest](symbols/hyperproc.quality._band_nearest.md) — internal
- [build](symbols/hyperproc.quality.build.md)
- [decode](symbols/hyperproc.quality.decode.md)
- [set_flag](symbols/hyperproc.quality.set_flag.md)
- [summary](symbols/hyperproc.quality.summary.md)
- [apply](symbols/hyperproc.quality.apply.md)
- [describe](symbols/hyperproc.quality.describe.md)

## Constant expressions

- [FLAGS](constants/hyperproc.quality.FLAGS.md)
- [FLAG_DESCRIPTIONS](constants/hyperproc.quality.FLAG_DESCRIPTIONS.md)
- [DEFAULT_DROP](constants/hyperproc.quality.DEFAULT_DROP.md)
- [BOOLEAN_SOURCES](constants/hyperproc.quality.BOOLEAN_SOURCES.md)
- [CODED_SOURCES](constants/hyperproc.quality.CODED_SOURCES.md)
- [_DTYPE](constants/hyperproc.quality._DTYPE.md)
- [_DTYPE_ONE](constants/hyperproc.quality._DTYPE_ONE.md)
