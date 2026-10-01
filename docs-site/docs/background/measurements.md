# Measurements and product levels

## Digital numbers, radiance, and reflectance

**Digital numbers (DN)** are stored detector or product values. Their scale factors, offsets, and fill values are part of the measurement definition. A value of 10,000 is not necessarily a reflectance of 10,000.

**Radiance** is a directional spectral energy measurement. A spectral density stated per nanometre is numerically different from one stated per micrometre; square-centimetre and square-metre units differ as well. Reader scaling and conversion to atmospheric-model units are separate operations.

**Reflectance** is dimensionless, but its meaning depends on atmospheric processing and geometry. Top-of-atmosphere reflectance still contains atmospheric contributions; surface reflectance is not automatically normalized for terrain or viewing direction. Values slightly outside zero to one can occur in real retrievals and must be assessed rather than silently clipped.

## Levels are provider-specific

| Product | Meaning in this implementation | Consequence |
|---|---|---|
| AVIRIS L1B | At-sensor radiance | Candidate input to the atmospheric pathway |
| AVIRIS L2A | Surface reflectance | Begin with QA and optional surface corrections |
| NEON DP1 / `L1` | Surface directional reflectance | Do **not** interpret the label as raw radiance |
| PACE OCI L1B | TOA reflectance (`rhot`) | Its ISOFIT route needs a dedicated conversion, not a simple unit factor |
| PACE OCI L2 SFREFL | Surface reflectance (`rhos`) | This reader is not a generic ocean-colour `Rrs` reader |
| PRISMA L2B | At-surface radiance | Not interchangeable with reflectance or L1 at-sensor radiance |
| PRISMA L2C / L2D | Surface reflectance, swath / mapped | The grid is a separate distinction from radiometric level |
| EnMAP / DESIS L1B vs L1C | Radiance, sensor grid vs mapped grid | L1C is not surface reflectance |

## Wavelength and spectral response

`wavelength` describes band centres in nanometres. `fwhm` describes an approximate band width where available. Neither necessarily contains the full spectral response function (SRF). A narrow absorption sampled by a coarse instrument may be unresolved even when a nominal band centre falls inside it.

`band_index` tracks the original source-band positions through supported selections and sorting. It is not a wavelength and should not be used as a cross-sensor scientific definition.

`good_wavelength` identifies usable bands according to available provider metadata or a documented fallback. It does not make a measurement error-free. Check `good_bands_source` and the reader-specific notes, especially around water-vapour absorption and detector joins.

## Before comparing two products

Confirm physical quantity, units, scaling, wavelength support, SRFs, spatial footprint, acquisition time, quality masks, angular geometry, and processing history. Spectral resampling addresses one part of this comparison, not all of it.
