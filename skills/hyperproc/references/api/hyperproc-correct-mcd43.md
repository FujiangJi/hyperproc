# hyperproc.correct.mcd43

Release baseline **0.1.2**; source `hyperproc/correct/mcd43.py`. Choose a callable below rather than loading every declaration.

MODIS MCD43A1 BRDF model parameters, the input to satellite BRDF normalisation.

MCD43A1 is a daily product: for every 500 m cell it gives the three weights of
the RossThick-LiSparseReciprocal model (``iso``, ``vol``, ``geo``) for MODIS
bands 1-7, fitted to all cloud-free observations in a 16-day window centred on
the date. Those weights describe the shape of the surface reflectance as a
function of Sun and view angle, which is exactly what a single hyperspectral
scene cannot know about itself.

    from hyperproc.correct import mcd43
    p = mcd43.fetch(bounds=(-121.0, 34.0, -119.8, 35.1), date="2023-04-22",
                    out_dir="cache/mcd43")
    par = p.sample(lon, lat)          # (..., 7 MODIS bands, 3 kernels)

Sources
-------
``source="gee"``
    Google Earth Engine, collection ``MODIS/061/MCD43A1`` (plus ``MCD43A2``
    for the per-band quality and snow flags). Needs ``earthengine-api`` and a
    one-off ``earthengine authenticate``; recent versions also need a Cloud
    project (``project=`` or ``$EARTHENGINE_PROJECT``). Downloaded in tiles
    through ``getDownloadURL`` so no other client library is required.
``source="local"``
    A GeoTIFF written by an earlier ``fetch``, or any 21-band stack whose band
    descriptions are the MCD43A1 parameter names.

Resolution
----------
MCD43A1 is a 500 m product, and 1/240 degree (about 464 m) is its native step.
``fetch(res=None)``, the default, adapts to the image: it never asks for a grid
finer than native, because upsampling adds no information that bilinear
sampling at each pixel's own coordinates does not already give, and it asks for
a coarser grid when the image pixels are coarser, so that MODIS cells are
**averaged** over the footprint instead of point-sampled. PACE OCI is the case
that needs this: its 1.2 km pixels each cover about six MODIS cells, and a
bilinear sample of the four nearest ones would alias. The coarse grids stay
whole multiples of the native step, so an aggregation always covers whole
MODIS cells. :func:`resolution_of` reports what a dataset asks for.

The download is cached: the same bounds, date and resolution give the same
file name under ``$HYPERPROC_CACHE_DIR/mcd43`` (or ``out_dir``), and an
existing file is reused unless ``overwrite=True``.

Fill values
-----------
Earth Engine delivers masked cells as zero, and zero is a legal parameter
value, so the image is unmasked to the product's own fill (32767) before the
download and only that value counts as "no data". Valid parameters are scaled
by 0.001 into reflectance units.

## Declared exports

`MODIS_BANDS`, `MODIS_RANGES`, `MODIS_CENTRES`, `KERNELS`, `PARAM_BANDS`, `Params`, `cache_dir`, `fetch`, `read`, `grid_for`, `bounds_of`, `date_of`, `resolution_of`, `step_for`, `available`

## Declared callables and classes

- [cache_dir](symbols/hyperproc.correct.mcd43.cache_dir.md)
- [read](symbols/hyperproc.correct.mcd43.read.md)
- [bounds_of](symbols/hyperproc.correct.mcd43.bounds_of.md)
- [date_of](symbols/hyperproc.correct.mcd43.date_of.md)
- [available](symbols/hyperproc.correct.mcd43.available.md)
- [resolution_of](symbols/hyperproc.correct.mcd43.resolution_of.md)
- [step_for](symbols/hyperproc.correct.mcd43.step_for.md)
- [grid_for](symbols/hyperproc.correct.mcd43.grid_for.md)
- [_init_ee](symbols/hyperproc.correct.mcd43._init_ee.md) — internal
- [_ee_image](symbols/hyperproc.correct.mcd43._ee_image.md) — internal
- [_aggregate](symbols/hyperproc.correct.mcd43._aggregate.md) — internal
- [_download](symbols/hyperproc.correct.mcd43._download.md) — internal
- [fetch](symbols/hyperproc.correct.mcd43.fetch.md)
- [Params](symbols/hyperproc.correct.mcd43.Params.md)

## Constant expressions

- [MODIS_RANGES](constants/hyperproc.correct.mcd43.MODIS_RANGES.md)
- [MODIS_BANDS](constants/hyperproc.correct.mcd43.MODIS_BANDS.md)
- [MODIS_CENTRES](constants/hyperproc.correct.mcd43.MODIS_CENTRES.md)
- [KERNELS](constants/hyperproc.correct.mcd43.KERNELS.md)
- [PARAM_BANDS](constants/hyperproc.correct.mcd43.PARAM_BANDS.md)
- [QA_BANDS](constants/hyperproc.correct.mcd43.QA_BANDS.md)
- [COLLECTION](constants/hyperproc.correct.mcd43.COLLECTION.md)
- [QA_COLLECTION](constants/hyperproc.correct.mcd43.QA_COLLECTION.md)
- [SCALE](constants/hyperproc.correct.mcd43.SCALE.md)
- [FILL](constants/hyperproc.correct.mcd43.FILL.md)
- [QA_FILL](constants/hyperproc.correct.mcd43.QA_FILL.md)
- [RES_DEG](constants/hyperproc.correct.mcd43.RES_DEG.md)
- [TILE](constants/hyperproc.correct.mcd43.TILE.md)
