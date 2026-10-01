# Export and provenance

## Spectral cubes

```python
hp.to_geotiff(mapped, "products/reflectance.tif", overviews=True)
hp.to_envi(mapped, "products/reflectance.img", interleave="bil")
hp.bands_to_csv(mapped, "products/reflectance_bands.csv")
```

| Output | What this implementation writes | Trade-off |
|---|---|---|
| GeoTIFF | Wavelength band descriptions, spatial metadata, selected scene tags | Compression and GIS-friendly overviews; keep the band CSV for numeric spectral metadata |
| ENVI | Binary cube plus header with wavelength, FWHM where available, and bad-band list | Rich spectral fields; larger uncompressed output |
| Band CSV | Wavelength, width, and good-band status | Keep it paired with the exact exported band order |
| Geometry rasters | Selected solar/view/terrain layers | Not implicitly contained in the reflectance raster |

GeoTIFF can carry custom metadata in general; the limitation here is what hyperproc's writer currently standardizes, not a universal impossibility of representing spectral metadata in that file format.

## Two-dimensional layers

```python
hp.export_geometry(mapped, "products/geometry")
hp.to_geotiff_2d(mapped, "products/elevation.tif", var="elev")
```

Do not export a sensor-grid cube with an invented CRS. Use the relevant mapping pathway first. For flags, use categorical-safe overview resampling and store flag definitions.

## Which calls write provenance?

`hc.export()` writes correction outputs with associated band/provenance files. `atmos.process()` writes its main product and requested auxiliary outputs. Calling a low-level raster writer alone does **not** promise the same complete provenance package. Explicitly preserve dataset attributes, coefficient JSON, quality definitions, and scene identity in custom workflows.

## Reopening exports

`hp.open()` identifies supported **provider products**. It is not a general round-trip reader for arbitrary hyperproc exports. Tutorial `load_product()` helpers use rasterio and reconstruct a dataset, but are notebook-local code, not a package API.

A reconstructed dataset must restore valid spectral coordinates, bad-band handling, units, spatial transform, geometry, and applicable quality information. Merely copying arrays from a same-shaped scene is unsafe. The current tutorial helper does not restore every original metadata field.

## Validate on disk

Reopen a small output with rasterio; check CRS, full affine, band count/order, nodata, selected values, and window location. Compare NaN patterns and rotated-grid corners as well as summary statistics. Preserve originals and choose distinct output directories for exploratory runs.

See [I/O API](../api/hyperproc-io.md) and [coefficient containers](../api/hyperproc-correct-coefficients.md).
