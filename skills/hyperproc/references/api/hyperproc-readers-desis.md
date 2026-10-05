# hyperproc.readers.desis

Release baseline **0.1.2**; source `hyperproc/readers/desis.py`. Choose a callable below rather than loading every declaration.

DESIS (DLR Earth Sensing Imaging Spectrometer) reader for L1B / L1C / L2A.

DESIS flew on the ISS MUSES platform from 2018 until the mission ended on
2023-12-31, so these are archive products. It is a **VNIR-only** instrument:
235 bands from 401 to 1000 nm, 30 m, with no SWIR at all.

Each product is a plain GeoTIFF of ``int16`` DN plus an XML sidecar, so unlike
EMIT or PRISMA nothing is self-describing - the wavelengths, the per-band
scaling and every viewing angle live in ``*-METADATA.xml``:

    value = DN * gainOfBand + offsetOfBand

L2A uses a single gain of 1e-4 with zero offset. **L1B and L1C carry a
different gain *and* a different offset for every one of the 235 bands**, so
applying a scene-wide scale factor - the obvious shortcut - is wrong there.

============  =========================  =============  ==================
level         grid                       variable       georeferencing
============  =========================  =============  ==================
L1B           1024 x 1024 sensor grid    radiance       none
L1C           1493 x 1493 UTM, 30 m      radiance       EPSG + transform
L2A           1493 x 1493 UTM, 30 m      reflectance    EPSG + transform
============  =========================  =============  ==================

Angles are **scene-level scalars**, not per-pixel rasters, and land in
``ds.attrs``: DESIS ships no equivalent of EMIT's OBS file.

## Imported aliases

- `crs_text` → `hyperproc.readers._common.crs_text`
- `finish_bands` → `hyperproc.readers._common.finish_bands`
- `normalise_angles` → `hyperproc.readers._common.normalise_angles`

## Declared callables and classes

- [open_desis](symbols/hyperproc.readers.desis.open_desis.md)
- [_sibling](symbols/hyperproc.readers.desis._sibling.md) — internal
- [_parse_metadata](symbols/hyperproc.readers.desis._parse_metadata.md) — internal
- [_add_quality](symbols/hyperproc.readers.desis._add_quality.md) — internal
- [_add_band_quality](symbols/hyperproc.readers.desis._add_band_quality.md) — internal

## Constant expressions

- [NODATA](constants/hyperproc.readers.desis.NODATA.md)
- [LEVEL_SPEC](constants/hyperproc.readers.desis.LEVEL_SPEC.md)
- [QUALITY_FLAGS](constants/hyperproc.readers.desis.QUALITY_FLAGS.md)
- [QUALITY_VALUES](constants/hyperproc.readers.desis.QUALITY_VALUES.md)
- [SCENE_TAGS](constants/hyperproc.readers.desis.SCENE_TAGS.md)
- [_GRANULE](constants/hyperproc.readers.desis._GRANULE.md)
