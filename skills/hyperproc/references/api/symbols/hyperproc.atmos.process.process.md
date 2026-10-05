# hyperproc.atmos.process.process

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def process(source, out_dir, work_dir=None, engine: str='sRTMnet', stages=('ac',), workers: int=24, window: dict | None=None, overviews=True, layers=('aot550', 'h2o'), uncertainty: bool=False, like: xr.Dataset | None=None, brdf: dict | None=None, quality: bool | dict=True, format: str='GTiff', overwrite: bool=False, verbose: bool=True, **ac_kwargs) -> dict
```

Run the requested stages on an L1B granule and write GeoTIFF products.

Args:
    source: the L1B file (opened with the sensor-grid option where the
        reader has one) or an already opened hyperproc L1B dataset.
    out_dir: where the products go. The reflectance is
        ``<stem>_<stages joined by _>.tif`` (``..._ac.tif``), with a band
        CSV and a provenance JSON beside it, and one small GeoTIFF per
        entry of ``layers`` (``..._ac_aot550.tif``, ``..._ac_h2o.tif``).
    work_dir: ISOFIT working directory; default ``out_dir/isofit_work/<stem>``.
        Reused when it already holds a finished run (see :func:`correct`).
    engine, workers, **ac_kwargs: passed to :func:`hyperproc.atmos.correct`
        (``atmosphere``, ``surface``, ``segmentation_size``, ``line``, ...).
    stages: ``("ac",)`` for atmospheric correction only. ``("ac", "brdf")``
        also normalises the Sun and view geometry with the MODIS c-factor
        (:func:`hyperproc.correct.nbar`) before the product is projected,
        and names the product ``<stem>_ac_brdf.tif``. Airborne flightlines
        are not corrected this way: FlexBRDF is fitted on a flightline
        group in :mod:`hyperproc.correct` instead.
    brdf: options for the BRDF stage, passed to
        :func:`hyperproc.correct.nbar` (``sza_ref``, ``spectral``,
        ``params``, ``cache_dir``, ``project``, ...).
    format: ``"GTiff"`` (default) or ``"ENVI"``. ENVI writes a flat binary
        with a ``.hdr`` that states the wavelengths, widths and bad-band
        list as numbers rather than as band labels, at the cost of no
        compression: a full EMIT product is about 5.1 GB against 2.2 GB.
        Overviews are not built for ENVI.
    quality: write ``<stem>_quality.tif``, the consolidated flag layer
        (:mod:`hyperproc.quality`), beside the product. A dict is passed
        through to :func:`hyperproc.quality.build`; False skips it.
    window: sensor-grid subset ``{"y": (y0, y1), "x": (x0, x1)}`` for
        trial runs; the product then covers only that footprint.
    overviews: internal pyramids on every GeoTIFF written (default True).
    layers: 2-D retrieval layers to write as separate GeoTIFFs.
    uncertainty: also write the posterior uncertainty cube (``..._uncert.tif``).
    like: for swath sensors, a projected dataset whose grid the product
        should reproduce (see :func:`to_map_grid`).
    overwrite: redo the ISOFIT retrieval even if the work dir holds one.

Returns:
    dict with ``reflectance`` (path), ``layers`` (name -> path),
    ``provenance`` (path), ``work_dir``, ``seconds`` and ``dataset``
    (the projected, lazy dataset that was written).

[Module and aliases](../hyperproc-atmos-process.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.process.process --runtime`.
