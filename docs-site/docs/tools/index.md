# Tools

Choose tools by processing stage and the physical meaning of your input. Each stage below points to its workflow and requirements.

<div class="entry-start" markdown>

**Which correction does your product need?**

Start with the input level, geometry, and scientific purpose. Provider surface reflectance does not automatically need another atmospheric correction.

[Choose a processing path →](../background/decision-guide.md)

</div>

<div class="tool-group" markdown>

## Inspect

<div markdown>

- [**Quality and masking →**](../workflows/quality.md)  
  Interpret quality flags and build masks before analysis or correction.
- [**Performance and large scenes →**](../workflows/performance.md)  
  Plan memory use, chunking, and processing scope.

</div>
</div>

<div class="tool-group" markdown>

## Correct

<div markdown>

- [**Atmospheric correction →**](../workflows/atmosphere.md)  
  Prepare supported radiance products for ISOFIT retrieval, including geometry, engines, and assets.
- [**Airborne terrain and BRDF →**](../workflows/airborne.md)  
  Inspect topographic diagnostics and grouped FlexBRDF processing for airborne reflectance.
- [**Satellite BRDF →**](../workflows/satellite.md)  
  Use MCD43-based angular normalization with local parameters or optional Earth Engine access.

</div>
</div>

<div class="tool-group" markdown>

## Analyze

<div markdown>

- [**Spectral processing →**](../workflows/spectral.md)  
  Smooth spectra, calculate derivatives, and remove continua.
- [**Spectral resampling →**](../workflows/resampling.md)  
  Match wavelength grids or published response functions.
- [**Features and indices →**](../workflows/features.md)  
  Calculate features from suitable measurements.

</div>
</div>

<div class="tool-group" markdown>

## Prepare outputs

<div markdown>

- [**Spatial alignment →**](../workflows/spatial.md)  
  Prepare common grids and align scenes.
- [**Export and provenance →**](../workflows/export.md)  
  Save products with their processing context.
- [**Validation and uncertainty →**](../workflows/validation.md)  
  Understand available checks and their limits.

</div>
</div>
