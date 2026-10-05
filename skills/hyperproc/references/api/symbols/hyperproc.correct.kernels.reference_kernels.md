# hyperproc.correct.kernels.reference_kernels

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def reference_kernels(sza_ref, volume='ross_thick', geometric='li_dense_r', b_r=1.0, h_b=2.0)
```

Kernels for the normalisation target: nadir view under solar zenith ``sza_ref``.

This is what a BRDF-normalised ("NBAR-like") reflectance is expressed at.
With ``vza = 0`` the relative azimuth is irrelevant; 0 is passed.

[Module and aliases](../hyperproc-correct-kernels.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.kernels.reference_kernels --runtime`.
