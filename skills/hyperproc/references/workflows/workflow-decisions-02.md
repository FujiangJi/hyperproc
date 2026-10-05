## Processing order and why

Atmospheric retrieval, topography, BRDF, georeferencing, spatial resampling, smoothing, and spectral resampling solve distinct problems. Do not substitute one for another. Surface reflectance normally skips atmospheric correction. Terrain and angular corrections depend on reflectance, reliable geometry, fitting support, and the research question. Avoid applying all available corrections by default.

Preserve original values or a lazy original dataset. Record intermediate physical meanings: derivative cubes are not reflectance; continuum removal is dimensionless spectral normalization; interpolated bands are estimates; response-resampled data are spectral simulations. If a transform retains a variable name or source attribute, that does not override its changed scientific meaning.

For cross-sensor comparisons, harmonized wavelength coordinates alone do not harmonize spectral response widths. A common map grid alone does not harmonize point-spread functions or acquisition conditions. Do not describe resampled hyperspectral spectra as actual Sentinel-2/Landsat observations.
