# Why hyperproc?

Imaging spectroscopy records a spectrum at each image pixel. Those spectra contain information about surface composition and condition, but they also reflect illumination, viewing geometry, the atmosphere, instrument response, and the mixture of materials within a pixel. An analysis-ready image is therefore more than a file that can be opened.

In terrestrial ecosystem research, spectral observations can support questions about vegetation condition, canopy composition, disturbance, and spatial heterogeneity. Connecting spectral features to ecological quantities still requires appropriate observations, calibration, validation, and models. The [NEON imaging-spectrometer overview](https://www.neonscience.org/data-collection/imaging-spectrometer) provides an introduction to these applications.

## The practical problem

Airborne and satellite archives do not deliver a common analytical object. Differences include file organization, dimension order, scale factors, units, wavelength metadata, detector overlaps, map grids, quality classes, and ancillary geometry. A workflow written against an EMIT NetCDF group cannot simply assume that PRISMA HDF-EOS, AVIRIS ENVI, and EnMAP raster products follow the same conventions.

Repeatedly translating these conventions in notebooks makes it easy to confuse radiance with reflectance, accidentally retain fill values, apply a band-number formula to the wrong wavelengths, or compare different ground footprints. These are the interoperability problems that hyperproc is designed to address.

## What the package contributes

1. **Archive discovery:** search by place/date across NASA, NEON, and DLR, with a common result record and an optional notebook map.
2. **Sensor-aware ingestion:** provider-specific readers decode supported products and retain their important distinctions.
3. **A shared analysis interface:** `xarray.Dataset` objects organize spectral cubes, wavelength coordinates, geometry, and quality information.
4. **Optional correction workflows:** ISOFIT atmospheric retrieval, airborne illumination/FlexBRDF processing, and satellite MCD43-based angular normalization.
5. **Spectral analysis tools:** band selection by wavelength, smoothing, derivatives, continuum removal, spectral resampling, and feature maps.
6. **Spatial and output tools:** swath gridding, translation-based coregistration, raster export, geometry layers, and processing records.

## What it does not establish automatically

A common interface is **not** proof that measurements from different sensors are physically interchangeable. Different spatial supports, spectral response functions, observation times, atmospheric assumptions, and angular conditions remain relevant. A common output grid does not remove those differences.

The current code is not a complete ecosystem monitoring service. It does not by itself provide a validated biomass model, species classifier, carbon-flux product, change-detection attribution system, or operational alert network. Its role is to support reproducible preparation and analysis of imaging-spectroscopy data for such work.

## Position in the scientific workflow

| Stage | hyperproc's role | Researcher's responsibility |
|---|---|---|
| Data selection | Search/download supported archives and read local products | Choose dates, sites, levels, and valid comparisons |
| Preparation | Decode, inspect, flag, correct, grid, export | Decide which corrections are scientifically justified |
| Spectral analysis | Produce transforms, indices, and absorption summaries | Connect features to ecological hypotheses |
| Interpretation | Retain useful provenance and diagnostics | Validate against independent evidence and quantify uncertainty |

## Relationship to other tools

The optional atmospheric pathway orchestrates [ISOFIT](https://isofit.github.io/isofit/latest/), which provides the inversion framework. hyperproc does not replace that retrieval model. [HyperCoast](https://hypercoast.org/) is another hyperspectral ecosystem, with an emphasis on visualization and coastal applications; it and ISOFIT informed this documentation's organization. Their code, capabilities, licenses, and scientific claims are not inherited by hyperproc.

Continue with [measurements and levels](measurements.md) and the [processing decision guide](decision-guide.md).
