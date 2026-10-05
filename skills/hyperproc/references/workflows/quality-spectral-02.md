## Wavelength addressing

Use `hp.band_at` or `spectral.bands.good_bands` and `runs_of_good_bands`. Default nearest-band tolerance is 20 nm. Record actual wavelengths selected. A 20 nm tolerance is a convenience default, not scientific permission for a narrow pigment/absorption feature. Check bad-band flags, wavelength order and monotonicity, gaps, and FWHM before fitting. Do not index “red band 50” across sensors.
