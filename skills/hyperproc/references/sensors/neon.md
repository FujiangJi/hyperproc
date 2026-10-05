Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/neon/](https://fujiangji.github.io/hyperproc/sensors/neon/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# NEON Airborne Observation Platform

The current reader supports **DP1.30006.001 reflectance flightlines**, not DP3 mosaics. NEON's `L1` label in this registry does not indicate at-sensor radiance.

```python
import hyperproc as hp
ds = hp.open("/path/to/NEON_DP1_reflectance.h5", sensor="NEON", level="L1")
hp.describe(ds)
```

The filename is a placeholder; provide a genuine DP1 HDF5 product with its provider hierarchy.

- [Decoding and geometry](neon-01.md)
- [Workflow](neon-02.md)
