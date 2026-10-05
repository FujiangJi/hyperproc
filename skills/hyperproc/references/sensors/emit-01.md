## Metadata and ancillary files

Keep corresponding OBS and MASK files available. The reader attaches geometry, quality, wavelength/FWHM, and location information when supported by the product and its siblings. Default `ortho=True` uses the GLT pathway; `ortho=False` retains the sensor-grid representation.

L1B radiance uses µW cm⁻² sr⁻¹ nm⁻¹ in this interface. L2A reflectance is dimensionless. Provider good-band information is not guaranteed in L1B; requesting provider-only bad-band masking can fail when it is unavailable.
