# hyperproc.correct.pipeline.mosaic_geotiffs

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def mosaic_geotiffs(paths, out_path, method: str='first', resampling: str='nearest', res: float | None=None, overviews=None, overview_resampling: str='average') -> Path
```

Merge GeoTIFFs into one north-up file.

Flight-aligned (rotated) grids - every AVIRIS line - are reprojected onto a
common north-up grid at the finest pixel size first, so lines with
different rotations can be mosaicked. ``method="first"`` keeps the first
file's value where they overlap (seams stay visible, which is what a
seam check wants); ``"mean"`` averages the overlap. ``overviews`` adds
internal pyramids to the result (see :func:`hyperproc.build_overviews`).

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.mosaic_geotiffs --runtime`.
