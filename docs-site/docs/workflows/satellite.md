# Satellite BRDF normalization

`hyperproc.correct.nbar()` uses MCD43 model parameters to estimate a ratio between modeled reflectance at target and observed geometry. That ratio multiplies the input reflectance. It does not fit a hyperspectral BRDF independently from one scene.

## Apply to suitable surface reflectance

```python
import hyperproc as hp
from hyperproc.correct import nbar

ds = hp.open("/path/to/satellite_surface_reflectance")
normalized = nbar(ds, sza_ref="observed", spectral="nearest", fill="none")
```

The example preserves observed solar zenith while normalizing the view. The function default is a fixed `sza_ref=45.0`, with nadir view. Choose deliberately; fixed-sun and observed-sun outputs answer different comparison questions.

If parameters are not supplied, the default retrieval pathway uses Google Earth Engine and requires external authorization. A local, already prepared parameter object can be passed through `params=`. Read [MCD43 API](../api/hyperproc-correct-mcd43.md) for supported local reading and fetching.

## Spatial and temporal support

MCD43A1 Version 6.1 provides model parameters at a much coarser support than many hyperspectral pixels and draws on a multi-day observation window. Sampling those parameters onto a fine grid does not create fine-resolution BRDF information. [NASA product description](https://data.nasa.gov/dataset/modis-terraaqua-brdf-albedo-model-parameters-daily-l3-global-500m-v061-53475).

## Spectral choices

| Setting | Behavior | Interpretation |
|---|---|---|
| `spectral="nearest"` | Assigns each spectral band to a nearby MODIS band | Traceable but potentially discontinuous at mapping boundaries |
| `spectral="interp"` | Interpolates parameter support in wavelength | Smoother approximation, not a new observation |
| `fill="none"` | Keeps a neutral multiplier where parameters are missing, with flags | Those pixels are not genuinely normalized |
| `fill="median"` / `"nearest"` | Substitutes parameters according to the selected policy | Requires explicit disclosure and QA |

A multiplicative scaling shared by all kernel coefficients cancels in the c-factor ratio. Arbitrary additive or component-specific parameter biases do **not** generally cancel. Treat broad claims about bias cancellation in historical docstrings cautiously.

## Quality and diagnostics

Inspect model quality, snow masking, footprint coverage, factor clipping, and any filled pixels. Review `c_factor`, associated flags, and provenance. Plot reflectance and factors across wavelength to detect mapping-boundary steps before fitting narrow absorption features.

The route is intended for suitable land surface reflectance. Applying a land BRDF model over water, snow, heterogeneous mixed pixels, or unusual angular conditions requires separate scientific justification.

See [c-factor API](../api/hyperproc-correct-cfactor.md) and the sensor-specific satellite notebooks.
