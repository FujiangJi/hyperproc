# hyperproc.spectral.smoothing._one_blas_thread

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _one_blas_thread()
```

Decorators: `contextmanager`.

Fit spectra with BLAS held to a single thread.

The spline solves one spectrum at a time, and each fit is a handful of
dense solves on a matrix the size of the knot count - a couple of hundred
rows. That is far below the size where threading a solve pays for itself,
so the BLAS threads only contend for cores. On a busy machine the tax is
not small: one Tanager spectrum that fits in 57 ms single-threaded took
38 s with 32 OpenBLAS threads fighting over it, a factor of 665.

Falls through quietly when threadpoolctl is not installed.

[Module and aliases](../hyperproc-spectral-smoothing.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.smoothing._one_blas_thread --runtime`.
