# EnMAP

EnMAP L1B and L1C are radiance products; L2A is surface reflectance. L1B detector grids are not automatically merged by this reader.

```python
mapped = hp.open("/path/to/ENMAP_L2A_SPECTRAL_IMAGE.TIF")
vnir = hp.open("/path/to/ENMAP_L1B_SPECTRAL_IMAGE_VNIR.TIF",
               sensor="ENMAP", level="L1B", cube="vnir")
```

Use real provider naming or an explicit matching sensor/level. Preserve the corresponding XML metadata and QA files.

## Important distinctions

- L1B opens one detector (`vnir` or `swir`) at a time. A merged, coregistered cube is not available merely by selecting `cube="full"`.
- Approximate L1B geocoding is not promoted to a trusted map CRS/transform.
- L1C/L2A support mapped products and the provider's available spectral organization.
- Per-band gains/offsets come from XML; nodata handling differs by level.
- The interface's L1 radiance units are W m⁻² sr⁻¹ nm⁻¹. Atmospheric input preparation performs a further unit conversion.
- Available angles are interpolated from scene-corner metadata; they are not independent per-pixel angle observations.

`quality=True`, `pixelmask`, `angles`, and `apply_scale` control optional behavior. Disabling scale conversion changes the physical interpretation of the cube and requires explicit downstream handling.

[Reader API](../api/hyperproc-readers-enmap.md) · [Window tutorial](../tutorials/enmap-window-tutorial.md)

## Archive delivery and example pairing

The current EnMAP example accepts both `SPECTRAL_IMAGE.TIF` and
`SPECTRAL_IMAGE_COG.TIF` deliveries. Its L1C/L2A pairing uses datatake,
acquisition start, and tile identity because the processing timestamps can
differ between levels. DLR download and policy requirements are described in
the [archive workflow](../workflows/search.md).
