# hyperproc.correct.topo.apply_topo

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def apply_topo(rho, cos_i, sza, slope=None, method='scs+c', c=None, mask=None, cos_i_min=0.0)
```

Apply a topographic correction to a ``(..., band)`` reflectance array.

Args:
    rho: reflectance with the band axis last.
    cos_i, sza, slope: per-pixel arrays (radians for the angles) matching
        ``rho.shape[:-1]``.
    method: one of :data:`METHODS`.
    c: for ``"c"`` / ``"scs+c"``, an array of length ``rho.shape[-1]`` with
        one C per band, or None for bands that must not be corrected.
    mask: boolean ``rho.shape[:-1]``; False pixels are returned unchanged.
    cos_i_min: pixels with ``cos i`` at or below this are left unchanged
        (the factor blows up towards grazing incidence).

Returns:
    Corrected array, float32, same shape. Bands whose C is None are
    returned unchanged - never silently "corrected" by a factor of 1
    dressed up as a result.

[Module and aliases](../hyperproc-correct-topo.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.topo.apply_topo --runtime`.
