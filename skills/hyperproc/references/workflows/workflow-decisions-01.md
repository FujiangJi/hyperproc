## Resolve meaning before choosing functions

Identify the observable (at-sensor radiance, TOA reflectance, surface radiance, surface reflectance), units/scaling, grid, usable wavelengths, QA sources, acquisition date/time, and provider processing history. Reader availability is only ingestion support, not proof that every correction can be applied or scientifically validated.

| User goal and data | Preferred branch | Information that would change the choice |
|---|---|---|
| NDVI/absorption map from suitable surface reflectance | Inspect → region → explicit QA → optional justified mapping → feature → export/check | Missing bands, cloud information, radiance/TOA input, invalid CRS |
| Compare spectra across sensors | QA → common physical quantity → matched spectral responses → matching ground/time → comparison | Sensor SRF support, scale/PSF differences, geometry, spectral gaps |
| Surface retrieval from supported at-sensor input | Asset/geometry/radiometry check → bounded ISOFIT → retrieval QA → mapping/export | Product not at-sensor input, no elevation/geolocation, unusable engine/priors |
| Normalize airborne reflectance flightlines | Representative sampling → topo diagnostics → evidence-gated topo → angular screening/group BRDF → apply/held-out evaluation | Poor angular diversity, unrepresentative samples, provider already corrected, geometry convention |
| Normalize satellite surface reflectance | Explicit MCD43/geometry/target/filling choices → NBAR → factors/QA → compare | Land applicability, parameter temporal support, coarse/mixed pixels, invalid geometry |
| Geographic cube/mosaic output | Verify or construct valid mapping → registration if needed → common support → export | Unmapped detector grids, rotated affine, unsupported deformation |
| Find scenes | Anonymous bounded supported search → inspect candidates → authorized selected download | Credentials, access policy, disk, unsupported collection/level |
