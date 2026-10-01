# Performance and large scenes

## Begin with the size of the computation

An uncompressed float32 cube requires approximately `rows × columns × bands × 4` bytes for one copy. Intermediate arrays, geometry, uncertainty, masks, task graphs, and compression can multiply memory needs. File compression does not make in-memory arrays equally small.

## Use bounded experiments

Start with a representative window, select only necessary diagnostics, and measure peak memory and wall time. Separate input preparation, retrieval, correction fitting, lazy graph construction, and export timings. A cached atmospheric product or SRF file makes a repeat run different from a first run.

The airborne tutorial's 2,000-row full-width fitting region is a performance compromise, not a generally proven minimum sample size. Keep enough across-track geometry and along-track ecological/terrain variability to support the selected model.

## Lazy operations still perform work

`.values`, `.compute()`, `.persist()`, plotting, and export may materialize data. A strided diagnostic can touch many compressed chunks even if it returns few pixels. Avoid loading the full cube merely to print a summary.

## Export and parallelism

The cube writer uses bounded row strips for Dask-backed output to reduce repeated partial writes. ENVI lacks GeoTIFF compression; output size can be substantial. Tune worker count and `block_bytes` conservatively and avoid stacking maximum Dask, GDAL, and ISOFIT parallelism on the same machine.

## Reproducible benchmarks

**Awaiting validation:** a public performance benchmark across sensors and machines. When constructing it, report hardware, storage, dependency versions, scene dimensions, compression, region, cache state, output format, worker counts, elapsed time, and peak memory. Do not transfer a single notebook's timing into a general package claim.
