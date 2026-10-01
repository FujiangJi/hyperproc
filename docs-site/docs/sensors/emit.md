# EMIT

The EMIT reader handles **L1B RAD** radiance and **L2A RFL** reflectance NetCDF products. It reads provider groups and can use the granule's geolocation lookup table (GLT) to map the cube.

```python
ds = hp.open("/path/to/EMIT_L2A_RFL_product.nc")
# Sensor-grid input is useful for the dedicated atmospheric workflow.
raw = hp.open("/path/to/EMIT_L1B_RAD_product.nc", ortho=False)
```

## Metadata and ancillary files

Keep corresponding OBS and MASK files available. The reader attaches geometry, quality, wavelength/FWHM, and location information when supported by the product and its siblings. Default `ortho=True` uses the GLT pathway; `ortho=False` retains the sensor-grid representation.

L1B radiance uses µW cm⁻² sr⁻¹ nm⁻¹ in this interface. L2A reflectance is dimensionless. Provider good-band information is not guaranteed in L1B; requesting provider-only bad-band masking can fail when it is unavailable.

## Processing

Start L2A analysis with QA. Optional satellite NBAR is distinct from atmospheric correction. For L1B, `atmos.process()` handles the sensor-grid retrieval and subsequent GLT mapping; do not manually alter geometry merely to satisfy a raster writer.

The saved whole-scene and window notebooks show example workflows, not a guarantee for every collection version or granule.

[Reader API](../api/hyperproc-readers-emit.md) · [Window tutorial](../tutorials/emit-window-tutorial.md) · [Whole-scene tutorial](../tutorials/emit-tutorial.md)
