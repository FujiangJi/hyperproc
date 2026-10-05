Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/prisma/](https://fujiangji.github.io/hyperproc/sensors/prisma/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# PRISMA

PRISMA support covers four product levels with different meanings:

| Level | Quantity | Spatial representation |
|---|---|---|
| L1 | At-sensor radiance | Swath |
| L2B | At-surface radiance | Geolocated swath |
| L2C | Surface reflectance | Geolocated swath |
| L2D | Surface reflectance | Mapped grid |

```python
ds = hp.open("/path/to/PRS_L2D_STD_product.he5", join_priority="swir")
```

- [Detector handling](prisma-01.md)
- [Geometry and quality](prisma-02.md)
- [Analysis](prisma-03.md)
