Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/pace/](https://fujiangji.github.io/hyperproc/sensors/pace/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# PACE OCI

This reader handles **L1B TOA reflectance** and **L2 SFREFL surface reflectance**. It is not a general reader for every PACE L2 ocean-colour variable.

```python
ds = hp.open("/path/to/PACE_OCI.product.L2.SFREFL.nc")
print(ds.attrs.get("level"), ds.attrs.get("units"))
```

- [Spectral organization](pace-01.md)
- [Geometry and mapping](pace-02.md)
- [Atmospheric and terrestrial use](pace-03.md)
