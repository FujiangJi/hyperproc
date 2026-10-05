# hyperproc.readers.aviris._chunks_for

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _chunks_for(cube: Path, spec, nx: int | None=None, nbands: int | None=None)
```

Turn ``chunks="auto"`` into a spec that matches how ENVI stores the cube.

Both interleaves AVIRIS uses are line-major - BIL keeps a whole line of
every band together, BIP a whole line of every sample - so GDAL's block is
one image line. Dask's own "auto" chunks per band instead, which makes a
small spatial subset pull every band in full: slicing 200x200 pixels out of
a 11 GB flightline reads all 11 GB. Chunking along ``y`` only, keeping all
bands and samples together, turns that into one sequential read.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._chunks_for --runtime`.
