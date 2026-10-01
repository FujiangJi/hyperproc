# Package architecture

```text
hyperproc/
├── __init__.py        Public convenience API and open/read dispatch
├── registry.py        Sensor/level discovery and loader registry
├── archive/           CMR, NEON, DLR search/download, common results, notebook map
├── readers/           Provider-specific decoding plus shared conventions
├── correct/           Airborne models, satellite c-factors, masks, coefficients
├── atmos/             ISOFIT inputs, engines, orchestration, assets, mapping
├── spectral/          Band selection, transforms, response functions, resampling
├── features.py        Indices and absorption summaries
├── quality.py         Common bit flags and masking
├── geometry.py        Terrain/angle convention checks
├── grid.py            Geolocation and regular-grid helpers
├── align.py           Translation estimation and coregistration
├── io.py              Raster, geometry, spectral metadata export
└── report.py          Human-readable dataset summaries
```

## Boundaries

Archive backends discover and fetch provider deliveries through common `Granule`/`Results` records; the notebook map is an optional, lazily loaded interface. Reader coverage is broader than archive-search coverage.

Readers decode measurements; they should not silently impose a scientific correction merely to make a downstream result look better. The shared dataset contract enables composition, while product-specific meaning remains in variables and metadata.

Airborne correction uses sample and coefficient containers to separate fitting from applying. Satellite normalization uses externally supported angular model parameters. The atmospheric package delegates the inversion to ISOFIT and introduces additional environment and file-lifecycle requirements.

## Public and internal APIs

Top-level exports provide convenient aliases, such as `quality_flags` for `quality.build` and `spectral_index` for `features.index`. The generated reference lists those mappings. An underscore-prefixed helper is not a stable public contract. A method documented automatically because it exists is not necessarily intended for user extension.

## Documentation isolation

`docs-site/` is an independent documentation project. It statically parses local source and renders existing notebooks without importing hyperproc. It contains no sensor imagery, credentials, automatic downloads, or retrieval execution hooks.
