# hyperproc.report._thin

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _thin(da, target: int=_SAMPLE)
```

Read about ``target`` elements out of a cube. Returns (array, sampled).

Striding is the obvious way to do this and the wrong one: an AVIRIS cube is
chunked along ``y``, so ``[::40]`` touches every chunk and pulls all 11 GB
to print a median. Reading a few small blocks costs a handful of chunk
reads instead, and still samples the length of the flightline rather than
one corner of it.

The blocks are square-ish rather than whole rows because the two layouts
punish opposite things. ENVI BIL reads a full image line either way, so
narrowing ``x`` is free. AVIRIS-5's NetCDF is gzipped in ``(10, 256, 256)``
chunks, where one full row across 424 bands means decompressing 1.7 GB -
17 s for a single row, against a few for a whole block.

[Module and aliases](../hyperproc-report.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.report._thin --runtime`.
