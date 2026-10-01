# DESIS

DESIS is represented by L1B/L1C radiance and L2A surface-reflectance products. Its VNIR coverage does not supply SWIR features merely because the common package supports them for other sensors.

```python
ds = hp.open("/path/to/DESIS-HSI-L2A-product-SPECTRAL_IMAGE.tif")
print(hp.describe_indices(ds))
```

## Input requirements

The spectral raster must retain the matching XML metadata for wavelength, calibration, and geometry interpretation. L1B is a sensor-grid product; L1C and L2A are mapped products. The reader's radiance convention is mW cm⁻² sr⁻¹ µm⁻¹.

## Geometry and masks

Some angles are scene-level values. `sceneAzimuth` is not silently treated as view azimuth. Geometry may therefore be insufficient for a requested downstream operation even when reflectance can be read correctly.

Quality layers are available through `quality=True`, with optional band-level quality. Land/water cloud flags and other provider classes are translated where available. Missing fields remain missing rather than being invented.

## Analysis limitations

Query index availability and set wavelength tolerances appropriate to the sensor. Absorption features outside measured spectral support should fail or be excluded, not be interpreted from interpolation. Validate atmospheric and BRDF requirements for the particular level and metadata delivery.

[Reader API](../api/hyperproc-readers-desis.md) · [Window tutorial](../tutorials/desis-window-tutorial.md)
