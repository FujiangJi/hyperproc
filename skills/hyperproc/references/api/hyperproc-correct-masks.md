# hyperproc.correct.masks

Release baseline **0.1.2**; source `hyperproc/correct/masks.py`. Choose a callable below rather than loading every declaration.

Pixel masks the correction fits are drawn from.

A fit is only as good as its sample. Published correction workflows build
the sample from a few reusable pieces - an NDVI window, a
range on an ancillary layer, finiteness of the kernels, distance from the
swath edge - and the same pieces serve here. Each function returns a boolean
array that is True where a pixel is *usable*; :func:`combine` ANDs them.

:func:`zhai_cloud` is the spectral cloud/shadow test of Zhai et al. (2018),
written from the paper's equations, with the band choices (440, 550, 660,
850, 1570, 2110 nm) and the scene-adaptive thresholds the paper prescribes.

## Declared callables and classes

- [ndi](symbols/hyperproc.correct.masks.ndi.md)
- [ndi_mask](symbols/hyperproc.correct.masks.ndi_mask.md)
- [range_mask](symbols/hyperproc.correct.masks.range_mask.md)
- [kernel_finite](symbols/hyperproc.correct.masks.kernel_finite.md)
- [edge_mask](symbols/hyperproc.correct.masks.edge_mask.md)
- [combine](symbols/hyperproc.correct.masks.combine.md)
- [sample_indices](symbols/hyperproc.correct.masks.sample_indices.md)
- [_zhai_indices](symbols/hyperproc.correct.masks._zhai_indices.md) — internal
- [zhai_stats](symbols/hyperproc.correct.masks.zhai_stats.md)
- [zhai_thresholds](symbols/hyperproc.correct.masks.zhai_thresholds.md)
- [zhai_cloud](symbols/hyperproc.correct.masks.zhai_cloud.md)
