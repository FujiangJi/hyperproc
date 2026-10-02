# Spectral resampling

Resampling maps a source spectrum onto another spectral support. It changes wavelength sampling/response, **not the spatial pixel size**.

## Choose the target

```python
# Regular target grid: spacing and bandwidth are separate choices.
coarser = hp.resample(ds, step=20, fwhm=25)

# Match another dataset's spectral coordinates/widths.
matched = hp.resample(ds, like=reference_ds)

# Integrate against a supported instrument response.
sentinel_like = hp.resample(ds, sensor="SENTINEL2A")
```

Explicit `wavelengths=` and `fwhm=` are also available. Gaussian, box, interpolation, and measured-response pathways are distinct models; a target centre alone does not define a complete response function.

## Response sources

The current SRF registry includes Sentinel-2A/B and Landsat 4/5/7/8/9 responses from agency sources. PlanetScope 4/8 entries are **nominal approximations from band edges**, not measured SRFs. Inspect `hyperproc.spectral.srf.available()` and retain the response source/cache provenance.

Install `pip install 'hyperproc[srf]'` to fetch and read published response
spreadsheets. It provides `requests` and `openpyxl`; ordinary spectral
transforms and explicit target-grid resampling do not require this extra.
Files default to `~/.cache/hyperproc/srf`, or the `srf` subdirectory under
`HYPERPROC_CACHE_DIR`.

## Coverage and resolution safeguards

`min_coverage=0.5` is the default support threshold. Unsupported target bands return NaN rather than being presented as fully measured. `band_coverage` helps distinguish sufficient from partial support. Evaluate whether the threshold is strict enough for your application; it is not an accuracy guarantee.

`allow_sharpening=False` prevents requesting narrower target responses than the source supports. Increasing sampling density cannot recover unresolved spectral detail. A 2 nm output grid does not turn an 8 nm instrument into a 2 nm instrument.

## Cross-sensor comparisons

An AVIRIS spectrum resampled to Sentinel-2 is a **spectral simulation**, not an observed Sentinel-2 pixel. Spatial response, geolocation, acquisition time, geometry, atmosphere, noise, and QA must still be reconciled. Co-registering pixels is likewise not sufficient to match their spatial point-spread functions.

Spectral uncertainty is not automatically propagated by the current resampling pathway. See [resampling API](../api/hyperproc-spectral-resampling.md) and [SRF API](../api/hyperproc-spectral-srf.md).
