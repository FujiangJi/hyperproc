# Tanager

The current reader targets orthorectified HDF5 radiance and surface-reflectance deliveries with `_ortho_radiance_hdf5.h5` and `_ortho_sr_hdf5.h5` naming patterns.

```python
ds = hp.open("/path/to/product_ortho_sr_hdf5.h5", uncertainty=False)
```

## Product interpretation

L1B radiance is represented in W m⁻² sr⁻¹ µm⁻¹; L2A surface reflectance is dimensionless. The reader extracts the HDF-EOS grid and reorders the cube to the common dimensions. Keep the complete HDF5 provider product rather than substituting an arbitrary raster export.

## Ancillary information

Available masks, geometry, retrieval layers, and optional uncertainty can be attached. Check the actual variables: the SR uncertainty layer can be named `reflectance_uncertainty`, while downstream functions may only recognize an `uncertainty` variable. Do not assume end-to-end propagation without inspecting the selected path.

Provider good-band information is level-dependent. The reader can mask flagged spectral values when requested; inspect dimensions and `good_wavelength` rather than assuming bad bands were physically removed.

## Workflow

Use the mapped reflectance directly for suitable quality-controlled analysis, or consider optional satellite NBAR with its scale and spectral-shape limitations. L1B retrieval requires the atmospheric environment and correct units. Access and redistribution permissions for source products remain the user's responsibility; no Tanager source data are bundled with this website.

[Reader API](../api/hyperproc-readers-tanager.md) · [Window tutorial](../tutorials/tanager-window-tutorial.md)
