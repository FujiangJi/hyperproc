## Validation appropriate to each output

- **Reader:** known scale/offset/nodata samples, expected spectral order, units, detector joins and sidecars. Registry resolution alone is insufficient.
- **QA:** bit meaning, source availability, selected exclusions, changed valid fraction and geometry/retrieval flag provenance.
- **Features:** exact formula and actual selected wavelengths, finite/invalid masks, divide/log domain, unsmoothed baseline and sensible bounded statistics. A plausible NDVI range alone does not prove correct units or geolocation.
- **Spectral transforms:** preserve unusable regions where intended, test analytic spectra and supported response integrals, identify synthesized/dropped bands and uncertainty treatment.
- **Atmosphere:** exact prepared input units/bands, retrieval phases/assets/priors/reuse, auxiliary layers/failed pixels, spectra across different surface classes and independent evidence where available.
- **Airborne corrections:** geometry convention, diagnostic gates, independent angular support, per-band coefficients, held-out flightlines/locations, seams and overlap by wavelength/class.
- **Satellite:** MCD43 time/space/quality, target angles, missing/filled/clipped factors, snow/water applicability and spectral-boundary discontinuities.
- **Grid/export:** actual CRS/full affine/corners/window ground extent, dimensions/band order/CSV, dtype/nodata, matching values/NaN patterns after reopening, categorical overviews.

Use known synthetic inputs for algorithm sanity checks and small real observed windows for integration. Existing test declarations are not evidence a suite was run. Offline tests do not prove live archive authentication or retrieval adequacy. Do not launch broad live downloads/retrievals merely to validate a skill bundle.
