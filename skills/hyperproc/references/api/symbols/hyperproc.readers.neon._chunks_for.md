# hyperproc.readers.neon._chunks_for

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _chunks_for(dset, spec)
```

Dask chunks: whole rows of the file's gzip chunk height, all bands.

Full-width rows make every chunk a complete GeoTIFF strip (the writer
otherwise rewrites each strip once per x-chunk) and read each gzip chunk
exactly once.

[Module and aliases](../hyperproc-readers-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.neon._chunks_for --runtime`.
