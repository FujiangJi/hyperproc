# hyperproc

Release baseline **0.1.2**; source `hyperproc/__init__.py`. Choose a callable below rather than loading every declaration.

hyperproc - one interface for airborne and spaceborne imaging spectroscopy.

    import hyperproc as hp

    ds = hp.open(path, sensor="EMIT", level="L2A")   # explicit
    ds = hp.open(path)                                # guessed from the filename
    hp.describe(ds)
    hp.list_readers()

Every reader returns an ``xarray.Dataset`` with the same shape of metadata:
``reflectance(y, x, wavelength)``, ``wavelength`` and ``fwhm`` coordinates in
nm, plus mask and geometry variables where the sensor provides them.

## Declared exports

`open`, `read`, `describe`, `list_readers`, `sniff`, `summary`, `to_geotiff`, `to_geotiff_2d`, `to_envi`, `to_raster`, `envi_header`, `FORMATS`, `build_overviews`, `bands_to_csv`, `main_var`, `default_name`, `export_geometry`, `GEOMETRY_LAYERS`, `check_geometry`, `fix_slope_convention`, `georeference`, `utm_epsg`, `latlon_grid`, `to_latlon_geotiff`, `smooth_spectra`, `align`, `coregister`, `estimate_shift`, `apply_shift`, `tie_points`, `quality`, `quality_flags`, `quality_apply`, `quality_decode`, `quality_summary`, `quality_table`, `features`, `spectral`, `band_at`, `band_depth`, `continuum_removal`, `describe_indices`, `resample`, `find_spikes`, `spline_gapfill`, `spectral_derivative`, `spectral_index`, `REGISTRY`, `Entry`, `__version__`, `archive`, `search`, `download`, `files`, `search_map`

## Imported aliases

- `REGISTRY` → `hyperproc.registry.REGISTRY`
- `Entry` → `hyperproc.registry.Entry`
- `list_readers` → `hyperproc.registry.list_readers`
- `resolve` → `hyperproc.registry.resolve`
- `sniff` → `hyperproc.registry.sniff`
- `summary` → `hyperproc.registry.summary`
- `apply_shift` → `hyperproc.align.apply_shift`
- `coregister` → `hyperproc.align.coregister`
- `estimate_shift` → `hyperproc.align.estimate_shift`
- `tie_points` → `hyperproc.align.tie_points`
- `georeference` → `hyperproc.grid.georeference`
- `latlon_grid` → `hyperproc.grid.latlon_grid`
- `utm_epsg` → `hyperproc.grid.utm_epsg`
- `FORMATS` → `hyperproc.io.FORMATS`
- `GEOMETRY_LAYERS` → `hyperproc.io.GEOMETRY_LAYERS`
- `bands_to_csv` → `hyperproc.io.bands_to_csv`
- `build_overviews` → `hyperproc.io.build_overviews`
- `default_name` → `hyperproc.io.default_name`
- `envi_header` → `hyperproc.io.envi_header`
- `export_geometry` → `hyperproc.io.export_geometry`
- `main_var` → `hyperproc.io.main_var`
- `to_envi` → `hyperproc.io.to_envi`
- `to_geotiff` → `hyperproc.io.to_geotiff`
- `to_geotiff_2d` → `hyperproc.io.to_geotiff_2d`
- `to_latlon_geotiff` → `hyperproc.io.to_latlon_geotiff`
- `to_raster` → `hyperproc.io.to_raster`
- `check_geometry` → `hyperproc.readers.aviris.check_geometry`
- `fix_slope_convention` → `hyperproc.readers.aviris.fix_slope_convention`
- `align` → `hyperproc.align`
- `archive` → `hyperproc.archive`
- `features` → `hyperproc.features`
- `quality` → `hyperproc.quality`
- `spectral` → `hyperproc.spectral`
- `download` → `hyperproc.archive.download`
- `files` → `hyperproc.archive.files`
- `search` → `hyperproc.archive.search`
- `band_depth` → `hyperproc.features.band_depth`
- `describe_indices` → `hyperproc.features.describe_indices`
- `spectral_index` → `hyperproc.features.index`
- `band_at` → `hyperproc.spectral.band_at`
- `continuum_removal` → `hyperproc.spectral.continuum_removal`
- `find_spikes` → `hyperproc.spectral.find_spikes`
- `resample` → `hyperproc.spectral.resample`
- `smooth_spectra` → `hyperproc.spectral.smooth_spectra`
- `spline_gapfill` → `hyperproc.spectral.spline_gapfill`
- `spectral_derivative` → `hyperproc.spectral.derivative`
- `quality_apply` → `hyperproc.quality.apply`
- `quality_flags` → `hyperproc.quality.build`
- `quality_decode` → `hyperproc.quality.decode`
- `quality_table` → `hyperproc.quality.describe`
- `quality_summary` → `hyperproc.quality.summary`
- `describe` → `hyperproc.report.describe`

## Declared callables and classes

- [open](symbols/hyperproc.open.md)
- [open_builtin](symbols/hyperproc.open_builtin.md)
- [__getattr__](symbols/hyperproc.__getattr__.md) — internal
