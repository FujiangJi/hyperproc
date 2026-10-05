# hyperproc.correct.cfactor.model_reflectance

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def model_reflectance(params, sza, vza, raa, volume: str='ross_thick', geometric: str='li_sparse_r', b_r: float=1.0, h_b: float=2.0)
```

Kernel-driven reflectance from MCD43A1 weights, ``(..., 7)``.

Args:
    params: ``(..., 7, 3)`` iso/vol/geo weights in reflectance units.
    sza, vza, raa: angles in degrees, broadcastable to ``params.shape[:-2]``.
    volume, geometric, b_r, h_b: kernel choice. The MODIS product is fitted
        with RossThick and LiSparseReciprocal at ``b_r=1, h_b=2``, so those
        are the only values that make its weights mean what they say.

[Module and aliases](../hyperproc-correct-cfactor.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.cfactor.model_reflectance --runtime`.
