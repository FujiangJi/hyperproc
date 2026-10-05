Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/desis/](https://fujiangji.github.io/hyperproc/sensors/desis/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# DESIS

DESIS is represented by L1B/L1C radiance and L2A surface-reflectance products. Its VNIR coverage does not supply SWIR features merely because the common package supports them for other sensors.

```python
ds = hp.open("/path/to/DESIS-HSI-L2A-product-SPECTRAL_IMAGE.tif")
print(hp.describe_indices(ds))
```

- [Input requirements](desis-01.md)
- [Geometry and masks](desis-02.md)
- [Analysis limitations](desis-03.md)
