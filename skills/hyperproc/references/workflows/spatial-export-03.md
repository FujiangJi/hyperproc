## Writer selection

| Entry | Appropriate output | Checks |
|---|---|---|
| `to_geotiff` | Main spectral cube, mapped | Band order, transform, CRS, nodata, compression, overviews |
| `to_envi` | Spectral binary + header | Interleave, dtype, wavelength/FWHM/bad-band list, map information |
| `to_raster` | Supported format dispatch | Actual format/extension and returned files |
| `to_geotiff_2d` | Named scalar/feature/geometry layer | Select variable explicitly; no cube assumptions |
| `to_latlon_geotiff` | Latitude/longitude bands, not a warped spectral cube | Two geographic-coordinate bands (or separate files); grid metadata follows the input |
| `export_geometry` | Available solar/view/terrain layers | Which layers exist; units and categorical handling |
| `bands_to_csv` | Numeric spectral band metadata | Must match exact exported order/count |
| `envi_header` | ENVI metadata generation | Header alone is not a complete binary product |
| `build_overviews` | Raster overview levels | Continuous versus categorical-safe resampling |
| `default_name` | Naming convention | Naming alone does not prevent collisions/prove provenance |
| `main_var` | Select main spectral cube | Confirm physical quantity before subsequent analysis |

Read [I/O exact signatures](../api/hyperproc-io.md). Writers materialize lazy arrays; memory-aware bounded strips help but do not remove full-output computation. Not all format choices support all metadata. GeoTIFF descriptions/tags do not replace the paired band CSV. ENVI contains richer standardized spectral metadata but can be much larger.

`hc.export()` includes correction-oriented provenance and band products; `atmos.process()` includes selected retrieval/geometry/QA outputs. A low-level raster write does not guarantee that entire provenance bundle. Preserve coefficients, flags, band support, source identifiers, units and processing manifest explicitly in custom workflows.
