## Important distinctions

- L1B opens one detector (`vnir` or `swir`) at a time. A merged, coregistered cube is not available merely by selecting `cube="full"`.
- Approximate L1B geocoding is not promoted to a trusted map CRS/transform.
- L1C/L2A support mapped products and the provider's available spectral organization.
- Per-band gains/offsets come from XML; nodata handling differs by level.
- The interface's L1 radiance units are W m⁻² sr⁻¹ nm⁻¹. Atmospheric input preparation performs a further unit conversion.
- Available angles are interpolated from scene-corner metadata; they are not independent per-pixel angle observations.

`quality=True`, `pixelmask`, `angles`, and `apply_scale` control optional behavior. Disabling scale conversion changes the physical interpretation of the cube and requires explicit downstream handling.

[Reader API](https://fujiangji.github.io/hyperproc/sensors/api/hyperproc-readers-enmap/) · [Window tutorial](https://fujiangji.github.io/hyperproc/sensors/tutorials/enmap-window-tutorial/)
