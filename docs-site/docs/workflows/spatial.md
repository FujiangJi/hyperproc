# Spatial grids and alignment

## Swath georeferencing

```python
mapped = hp.georeference(swath)
matched_grid = hp.georeference(swath, like=reference)
```

The current gridding path uses latitude/longitude and nearest-source gathering to form a regular grid while retaining source spectra. It is not a universal rigorous orthorectification engine for arbitrary raw instrument geometry. EMIT has a dedicated GLT pathway; many provider products already arrive mapped.

Default grid choices are sensor-dependent: PACE is treated differently from fine-resolution UTM scenes. Pass `epsg`, `resolution`, and `radius` deliberately when needed, and inspect the resulting transform. Filling small geometric holes is distinct from synthesizing missing spectral measurements.

## Translation-based coregistration

```python
diagnostic = hp.estimate_shift(moving, reference)
aligned = hp.coregister(moving, reference, resample=False)
```

Phase correlation estimates displacement using a selected wavelength and compares tile estimates for consistency. The default main-band wavelength is 860 nm. Featureless areas, clouds, different land conditions, spectral mismatch, or non-translational distortions can undermine the result.

`resample=False` adjusts georeferencing without resampling spectral pixels. `resample=True` resamples onto the reference grid. These operations have different consequences for spatial support and uncertainty. Inspect diagnostic strength and scatter before using `force=True`.

## Rotated grids and matching ground

Use the complete affine transform, not just `x`/`y` coordinates, when reasoning about rotated rasters. A shared array shape is not evidence that pixels represent the same location. The AVIRIS-3 tutorial's index-based comparison is appropriate only because the processing window is defined on the same known source grid.

Validation for more complex deformations, rotated cross-sensor cases, or incompatible grids remains **awaiting dedicated evidence**. Do not describe this method as a full bundle-adjustment or nonlinear registration system.

See [grid API](../api/hyperproc-grid.md), [alignment API](../api/hyperproc-align.md), and [geometry API](../api/hyperproc-geometry.md).
