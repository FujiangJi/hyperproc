# Existing surface reflectance → validated analysis product

Use this route for suitable provider reflectance (including NEON DP1 `L1`). It normally bypasses atmosphere. Identify actual quantity, available geometry/QA, bad bands and calibrated scaling first; don't assume every `reflectance` variable is surface reflectance (PACE L1B is TOA).

Example skeleton for a real mapped provider product:

```python
from pathlib import Path
import hyperproc as hp

source = Path("/data/actual_supported_surface_product")
ds = hp.open(source)
try:
    # Replace with a verified nonempty observed region on this source grid.
    win = ds.isel(y=slice(600, 800), x=slice(600, 800))
    hp.describe(win)
    q = hp.quality_flags(win, derive=("fill", "terrain_shadow"))
    clean = hp.quality_apply(win, q, drop=("fill", "cloud", "cloud_shadow", "cirrus"))
    ndvi = hp.spectral_index(clean, "NDVI")
    # These writers need a genuine mapped grid, not invented CRS attributes.
    hp.to_geotiff(clean, "/work/reflectance.tif")
    hp.bands_to_csv(clean, "/work/reflectance_bands.csv")
    hp.to_geotiff_2d(clean.assign(NDVI=ndvi), "/work/ndvi.tif", var="NDVI")
    hp.to_geotiff_2d(clean.assign(quality=q), "/work/quality.tif", var="quality",
                      tags=q.attrs, overview_resampling="nearest")
finally:
    ds.close()
```

The path/window are deliberate placeholders; validate region and output collisions before running. Missing cloud layers remain unknown, even if q has zero cloud bits. Integer QA metadata/bit definitions must survive export/provenance; verify written dtype and choose categorical-safe overviews. Add geometric mapping only for eligible swaths, using actual lat/lon/GLT, and document its spatial support. Do not promise arbitrary exported TIFFs can be reopened by `hp.open()`.

For spectral work, record exact selected bands/formulas; compute unsmoothed baseline features, justify optional smoothing/gap filling, preserve synthesized flags and assess sensitivity. An NDVI map is not itself a reflectance cube. Keep the reflectance, QA and band table as needed for subsequent science.

Apply airborne/satellite normalization only if the task and evidence call for it; use the separate route and retain its factors/coefficients. Finish [science-readiness checks](science-ready.md), reopen representative disk samples and write the generating script and manifest. A zero-filled/empty window is not a successful analysis just because the code completed.
