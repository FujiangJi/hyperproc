# Features and indices

Feature functions turn a spectral cube into one or more spatial maps. Use appropriate reflectance inputs and masks; a function accepting an array does not prove that the quantity is suitable.

## Named indices and formulas

```python
print(hp.describe_indices(ds))
ndvi = hp.spectral_index(ds, "NDVI")
custom = hp.spectral_index(ds, "(R800 - R670) / (R800 + R670)", name="custom_ndvi")
print(custom.attrs)
```

The registry currently contains NDVI, EVI, NDWI, NDII, PRI, NDNI, CAI, MCARI, ARI1, CRI1, PSRI, and NDSI. Names can have multiple definitions in the literature; inspect the exact formula and citation returned by `describe_indices()` rather than inferring a formula from its acronym.

`R800` means the nearest acceptable reflectance band to 800 nm, subject to tolerance and usable-band policy. The output records bands used. Expressions are parsed with a restricted syntax rather than evaluated as arbitrary Python.

## Absorption depth, position, and area

```python
feature = hp.band_depth(ds, "cellulose")
depth = feature["depth"]
position = feature["position"]
area = feature["area"]
```

Named windows include chlorophyll, water at 970/1200 nm, lignin at 1730 nm, cellulose, and clay at 2200 nm. A `(lower, upper)` interval can define a custom window. These are descriptive spectral features, not validated estimates of biochemical concentration.

Availability depends on source wavelength coverage, band quality, and resolution. DESIS, for example, does not gain SWIR absorption features by sharing an API with a full VNIR–SWIR instrument.

## Export a feature map

```python
output = mapped.assign(NDVI=hp.spectral_index(mapped, "NDVI"))
hp.to_geotiff_2d(output, "products/ndvi.tif", var="NDVI")
```

Here `mapped` must already carry a valid spatial reference. Keep the formula, actual selected wavelengths, masks, source product, and any preceding corrections with the exported map.

See [features API](../api/hyperproc-features.md).
