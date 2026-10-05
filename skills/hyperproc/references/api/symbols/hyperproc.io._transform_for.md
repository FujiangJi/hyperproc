# hyperproc.io._transform_for

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _transform_for(ds: xr.Dataset)
```

The affine to write, rebuilt from the dataset's own x/y coordinates.

``attrs["transform"]`` describes the granule as delivered, so it goes stale
the moment anyone subsets. rioxarray normally sidesteps that by deriving
the affine from the coordinates - but it cannot for the flight-aligned
AVIRIS grids, where rotation makes easting depend on the row as well as the
column, and it falls back to a north-up transform that puts the image in
the wrong place.

So: take the rotation and pixel size from ``attrs["transform"]``, and
recover the origin from where the coordinates actually start. The 1-D
``x``/``y`` are written as ``gt[0] + (col + 0.5) * gt[1]`` and
``gt[3] + (row + 0.5) * gt[5]``, so inverting them gives the subset's
offset exactly, and their spacing gives any stride.

Returns None when there is nothing better than rioxarray's own guess.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io._transform_for --runtime`.
