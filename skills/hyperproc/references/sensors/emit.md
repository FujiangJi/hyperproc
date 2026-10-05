Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/emit/](https://fujiangji.github.io/hyperproc/sensors/emit/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# EMIT

The EMIT reader handles **L1B RAD** radiance and **L2A RFL** reflectance NetCDF products. It reads provider groups and can use the granule's geolocation lookup table (GLT) to map the cube.

```python
ds = hp.open("/path/to/EMIT_L2A_RFL_product.nc")
# Sensor-grid input is useful for the dedicated atmospheric workflow.
raw = hp.open("/path/to/EMIT_L1B_RAD_product.nc", ortho=False)
```

- [Metadata and ancillary files](emit-01.md)
- [Processing](emit-02.md)
