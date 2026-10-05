# hyperproc.readers.aviris._glt_cube

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _glt_cube(cube: xr.DataArray, sample: np.ndarray, line: np.ndarray, tile: int=512) -> xr.DataArray
```

Orthorectify a ``(wavelength, y, x)`` cube through a JPL lookup table.

Done lazily and in tiles. The lazy part matters because the output here is
424 x 2009 x 3605 floats - 12 GB against the sensor grid's 4 GB, most of it
the void around a rotated flight strip - so materialising it to hand back a
dataset would defeat opening the cube lazily at all.

The tiling matters just as much. Gathering into chunks that span the whole
grid means any spatial subset, however small, computes every pixel of every
band in the chunk: a 100 x 100 window took minutes. Because the lookup
table is spatially coherent, each output tile only ever reads a bounded
window of the sensor grid, which is computed here at graph-build time.

Indices are 1-based with 0 for "no data"; a negative index marks a cell
filled from a neighbour rather than sampled directly, so both signs point at
a real pixel and only the zeros are dropped.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._glt_cube --runtime`.
