# hyperproc.correct.pipeline.export

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def export(ds: xr.Dataset, out_dir, wavelengths=None, window=None, suffix: str='', compress: str='deflate', workers: int=4, overviews=None, overview_resampling: str='average', format: str='GTiff') -> Path
```

Write the (corrected) cube as GeoTIFF or ENVI, + band CSV + provenance JSON.

``wavelengths`` selects bands by nearest wavelength (nm); ``window`` is
``(y0, y1, x0, x1)`` in pixels. Either makes the output a subset, and
``suffix`` should then say so in the file name. The provenance JSON
records the stages, coefficient sources and any subsetting. ``workers``
caps the dask threads while computing: every block holds a full-swath,
all-band slab, so a 14-thread default can exceed memory on 400-band cubes.
``overviews`` (``True`` or a list of factors) adds internal pyramids for GIS
display after the write, see :func:`hyperproc.build_overviews`.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.export --runtime`.
