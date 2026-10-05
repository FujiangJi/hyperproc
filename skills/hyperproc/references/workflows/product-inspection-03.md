## Dataset contract

The main cube normally has `(y, x, wavelength)` dimensions. Important spectral coordinates are `wavelength`, `fwhm`, `good_wavelength`, and `band_index` when supplied. Not every coordinate/layer exists on every product. Standard geometry names include `sza`, `saa`, `vza`, `vaa`, `raa`, `slope`, `aspect`, `cos_i`, and `elev`; swaths may include `lat`/`lon`. Dataset-facing angles are degrees, elevation normally metres, `cos_i` dimensionless, wavelengths/FWHM nm.

Mapped grids need real CRS and a full affine transform. Latitude/longitude alone is not a regular projected grid. A detector grid may require additional provider geolocation before mapping is possible. Inspect whether angles came from actual pixels, corners, interpolation, ephemeris, or broadcast scalars; broadcasting does not create independent angular observations.

For slope-convention questions use `hp.check_geometry(ds)` and inspect `checked`, `needs_fix`, and evidence. An unchecked empty window is not a passing diagnostic. `fix_slope_convention()` mutates the dataset in place; do not apply it twice or simply because the sensor name matches an example. Reader paths may already fix geometry. Preserve the recorded `geometry_fixed` attributes.

Reader errors: missing path → `FileNotFoundError`; unrecognized or invalid sensor/level → `ValueError`; planned reader → `NotImplementedError`; missing dependency/companion file → diagnose exactly. Preserve paths and naming on real delivery files instead of renaming to trick sniffing. `hp.describe()` samples data; it is not a metadata-only operation.
