Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/tanager/](https://fujiangji.github.io/hyperproc/sensors/tanager/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# Tanager

The current reader targets orthorectified HDF5 radiance and surface-reflectance deliveries with `_ortho_radiance_hdf5.h5` and `_ortho_sr_hdf5.h5` naming patterns.

```python
ds = hp.open("/path/to/product_ortho_sr_hdf5.h5", uncertainty=False)
```

- [Product interpretation](tanager-01.md)
- [Ancillary information](tanager-02.md)
- [Workflow](tanager-03.md)
