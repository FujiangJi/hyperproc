# Satellite surface reflectance → chosen angular reference

Use suitable land surface reflectance with real acquisition/solar/view geometry. This NBAR route uses MCD43 model parameters; it does not fit an independently observed hyperspectral BRDF from a single image.

Choose parameter source/date/footprint/QA, actual spatial/temporal support, target geometry, spectral mapping, filling and factor clipping deliberately. Coarse roughly 500 m/multi-day parameters sampled onto fine hyperspectral pixels do not become fine-scale BRDF observations.

```python
import hyperproc as hp
from hyperproc.correct import nbar

ds = hp.open("/data/actual_satellite_surface_product")
# Default external fetch needs authorized Earth Engine/project and transfer scope.
normalized = nbar(ds, sza_ref="observed", spectral="nearest", fill="none")
```

This normalizes view while retaining observed solar zenith. Default `sza_ref=45.0` answers a different comparison question. Use prepared local `params=` when available; inspect exact object support. `source="local"` means existing cache, not automatic missing-parameter downloads. `nbar(cache_dir=...)` and `mcd43.fetch(out_dir=...)` differ.

Plan any external parameter transfer before fetching. Earth Engine authentication/project authorization is separate from NASA/NEON/DLR credentials. Missing/fill support must remain visible in factor/validity QA: a neutral multiplier with `fill="none"` is not a successful physical normalization, and median/nearest substitution is an assumption.

Check snow/water/mixed pixels, factor clipping, coverage, geometry and spectral discontinuities at MODIS mapping boundaries. `spectral="interp"` is parameter interpolation, not new observations. Model-agreement/view-profile diagnostics can be untestable on small angular windows; report that result, not a fabricated correlation. A common coefficient scaling cancels in the c-factor ratio; arbitrary additive/component-specific biases do not generally cancel.

Normalize/export only when appropriate for the intended research. Retain original spectra, c_factor and flags, source/target geometry and parameter provenance; evaluate representative surfaces/wavelengths and finish [science readiness](science-ready.md). Exact [c-factor API](../api/hyperproc-correct-cfactor.md), [MCD43 API](../api/hyperproc-correct-mcd43.md), and [advanced corrections](advanced-corrections.md) provide detailed behavior.
