# Validation and uncertainty

## Evidence levels

1. **Source presence:** a function exists and its arguments can be documented.
2. **Execution evidence:** a particular input produced output in a particular environment.
3. **Numerical checks:** outputs match known answers or controlled invariants.
4. **Independent scientific validation:** held-out observations or external references support intended use.

These are different claims. The documentation build provides static reference generation and reproduces saved notebook outputs, not a new independent validation campaign.

## What the saved AVIRIS-3 example shows

The stored comparison near 865 nm reports median difference +0.0022, RMSE 0.0023, and correlation 0.9998 against provider L2A for a 500 × 500 window. This is one selected band and region, with retrieval reuse visible in the log. It is not a full-spectrum accuracy estimate or a fresh runtime benchmark.

The topographic diagnostics show `skip`, `inconclusive`, and `refuse`, not universal support for correction. The tutorial forces application for demonstration. Overlap agreement improves at some visible/NIR wavelengths and worsens in the displayed SWIR examples. Preserve both outcomes when reporting results.

## Suggested validation plan

| Component | Tests to establish |
|---|---|
| Readers | Known scale/offset/fill values, exact wavelength ordering, detector joins, shapes, and metadata |
| Geometry | Affine corner checks, rotation/subsets, angular conventions, independent terrain comparison |
| Atmospheric retrieval | Matched spectra, multiple surfaces/conditions, external atmospheric/reflectance evidence |
| Topographic correction | Held-out terrain/land-cover relationships; avoid fitting and judging on the same samples |
| BRDF | Held-out flightlines, angular residuals, overlap metrics by wavelength and class |
| Spectral transforms | Analytic spectra, gap preservation, feature distortion, numerical baseline comparisons |
| Resampling | Known response integrals, band coverage, no unsupported sharpening |
| Exports | Round-trip geometry, units, bands, nodata, QA meanings, and provenance |

## Uncertainty budget

Consider calibration and noise, atmospheric priors, surface-model assumptions, terrain/angle error, coarse BRDF parameter support, spectral interpolation, spatial registration, and model-transfer error. A provider uncertainty layer usually represents only part of this budget. Current transforms do not implement a complete end-to-end uncertainty propagation framework.

## Current limitation

**Awaiting validation:** a retained, automated, cross-sensor regression suite and independently reviewed scientific benchmarks. Historical comments referring to synthetic tests or external equivalence should be linked to actual fixtures and reproducible reports before being used as release claims.
