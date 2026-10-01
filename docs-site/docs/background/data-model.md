# Data model and geometry

## Dataset contract

Readers return an `xarray.Dataset`, usually with a Dask-backed main cube:

```text
Dataset
├── reflectance or radiance (y, x, wavelength)
├── coordinates: wavelength, fwhm, good_wavelength, band_index
├── spatial coordinates: x, y
├── available geometry: sza, saa, vza, vaa, raa, slope, aspect, cos_i, elev
├── available quality and retrieval layers
└── attributes: sensor, level, source, granule/stem, units, datetime,
                crs/transform when the product is mapped
```

This describes the intended shared structure, not a promise that every variable exists in every product. Provider-specific variables may coexist with standardized names. `hp.main_var(ds)` returns the selected cube variable.

## Geometry conventions

| Field | Meaning | Usual representation |
|---|---|---|
| `sza`, `saa` | Solar zenith and azimuth | Degrees |
| `vza`, `vaa` | View zenith and azimuth | Degrees |
| `raa` | Relative azimuth derived from view and sun azimuth | Degrees, wrapped |
| `slope`, `aspect` | Terrain inclination and direction | Degrees |
| `cos_i` | Cosine of local solar incidence | Dimensionless |
| `elev` | Elevation | Metres where supplied/derived accordingly |
| `lat`, `lon` | Pixel geolocation | Geographic degrees |

Reader geometry may be per-pixel, interpolated from corners, derived from ancillary files, or broadcast from a scene scalar. A two-dimensional array is not necessarily a two-dimensional measurement. Check the sensor guide and metadata before using small geometric variations in a fit.

Low-level kernel functions typically accept **radians**. Dataset-facing workflows convert the reader's degree-valued layers. Do not mix those interfaces.

## Mapped grids versus sensor grids

A mapped dataset carries a valid CRS and affine transform. A geolocated swath can have latitude/longitude arrays without a regular projected grid. A raw detector grid may have neither sufficient geolocation nor a usable CRS.

For a rotated affine grid, one-dimensional `x` and `y` axes cannot fully describe the position of each pixel. The full affine transform is authoritative. Spatial windows selected by indices retain their source-pixel identity; a naive coordinate lookup against another raster does not prove alignment.

## Laziness and computation

Opening a cube does not normally load every spectral value. However, metadata parsing and geometry checks perform I/O, `describe()` samples data, and `.values`, `.compute()`, plotting, or writing can trigger significant work. Dask chunking controls execution granularity, not the scientific interpretation of the data.

## Uncertainty

Some readers optionally expose uncertainty. Names and semantics vary, and not all transforms propagate all uncertainty variables. Several spectral transforms deliberately drop uncertainty. Never assume that an uncertainty cube remains valid merely because another variable with that name survives a workflow.
