## Resource controls

One float32 cube is `ny*nx*nb*4` bytes; masks, geometry, repeated intermediate cubes, compression buffers, graph overhead and uncertainty add more. A modest spatial window can still include hundreds of bands. `fraction` in airborne sampling does not cap all topographic mask/statistic reads. `.values`, plotting, fitting, computation and raster export are not metadata-only. Avoid full-scene `.persist()` unless measured resources justify it. Avoid oversubscribing Dask, GDAL, BLAS and ISOFIT simultaneously. Measure bounded work first.
