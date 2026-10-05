# hyperproc.correct.pipeline.sample_image

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def sample_image(ds: xr.Dataset, fraction: float=0.1, max_pixels: int | None=None, seed: int=0, edge_px: int=30, min_blocks: int=4, strategy: str='pixels', topo_calc: dict=TOPO_CALC, brdf_calc: dict=BRDF_CALC) -> Sample
```

Build the sample the fits are made from.

``strategy="pixels"`` (default) is the reference procedure: the **whole
flightline** is read once to build every mask on every pixel (valid,
NDVI, Zhai cloud/shadow with scene statistics, swath edge); a **random**
``fraction`` of the pixels passing the valid and NDVI masks is then drawn
and its full spectra read for the BRDF fit; and the topographic C is later
fitted on **all** pixels of the topo calc mask, from per-band regression
sums accumulated while reading (exactly the all-pixel NNLS/OLS result,
without holding the cube in memory). Cost: two passes over the cube.
``max_pixels`` caps the random draw (None = no cap; memory is
n x bands x 4 bytes).

``strategy="chunks"`` is the cheap alternative: ``fraction`` of the reader
chunks, spaced evenly over the chunk grid, are read and at most
``max_pixels`` (default 250,000) random pixels are kept from them; cloud
statistics and the NDVI population come from the chunks read only. One
tenth of a pass instead of two - use it for quick looks.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.sample_image --runtime`.
