Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/enmap/](https://fujiangji.github.io/hyperproc/sensors/enmap/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# EnMAP

EnMAP L1B and L1C are radiance products; L2A is surface reflectance. L1B detector grids are not automatically merged by this reader.

```python
mapped = hp.open("/path/to/ENMAP_L2A_SPECTRAL_IMAGE.TIF")
vnir = hp.open("/path/to/ENMAP_L1B_SPECTRAL_IMAGE_VNIR.TIF",
               sensor="ENMAP", level="L1B", cube="vnir")
```

Use real provider naming or an explicit matching sensor/level. Preserve the corresponding XML metadata and QA files.

- [Important distinctions](enmap-01.md)
- [Archive delivery and example pairing](enmap-02.md)
