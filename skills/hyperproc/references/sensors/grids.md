# Sensor/level grids: decide what window indices mean

`{y:(row0,row1),x:(col0,col1)}` is a half-open pixel window **on the dataset being processed**. Two equal index ranges are not automatically the same ground. Check source identity, dimensions, full CRS/affine or GLT/lat-lon mapping. The table describes baseline reader/processing behavior; actual metadata remains authoritative.

| Sensor | Lower-level input grid | Reflectance grid | Reuse indices? |
|---|---|---|---|
| EMIT L1B/L2A | `hp.open()` defaults `ortho=True` GLT mapping; atmospheric `process` opens L1B with `ortho=False` on sensor grid | Default L2A opening GLT-mapped | **Not between atmospheric sensor-grid windows and mapped L2A**. If both mapped, verify their actual transforms/extent first |
| PRISMA L1/L2B/L2C/L2D | L1 swath; L2B/L2C geolocated swaths, with different quantities | L2D mapped UTM; L2C swath reflectance | **Not L1-swath versus L2D-UTM indices**. Use verified ground mapping; matched swath geometry also needs verification |
| PACE L1B/L2 | L1B TOA reflectance on combined detector/swath support | Supported L2 SFREFL swath | Only when corresponding acquisition and per-pixel geolocation/shapes are verified; no automatic “same swath” guarantee |
| EnMAP L1B | **Separate VNIR and SWIR detector grids**, not co-registered; select `cube` | L2A merged mapped cube | **No**. Prefer appropriate L1C for a merged mapped radiance comparison |
| EnMAP L1C/L2A | Mapped radiance | Mapped surface reflectance | Conditional: verify same acquisition, complete affine/CRS/extent, not only UTM designation |
| DESIS L1B/L1C/L2A | L1B detector grid; L1C mapped radiance | L2A mapped reflectance | L1B: no. L1C/L2A: conditional on verified matching grids |
| Tanager L1B/L2A | Ortho radiance HDF5 | Ortho surface reflectance HDF5 | Conditional on actual acquisition/transform agreement |
| AVIRIS variants | ENVI/NetCDF variant-specific; AVIRIS-5 `ortho` choices can differ | Variant-specific reflectance/ORT | Conditional on actual flightline/grid/chunk identity; do not generalize all variants |
| NEON DP1 (`L1`) | Already ATCOR surface reflectance flightline | No implemented radiance-to-reflectance level pair | Compare only verified flightline grids; DP3 (`L3`) reader is not implemented |

For EMIT, the atmospheric window applies before GLT mapping and maps to a potentially different output extent/shape. A `[600:800,600:800]` region in that sensor cube is not the same region as that slice in default mapped L2A. PRISMA L1-to-L2D likewise needs geolocation/mapping. Keep the window's grid identity in provenance and work-directory context.

When possible use a known geographic region and verify its pixel mapping in each dataset. `hp.georeference(..., like=reference)` supports eligible swaths; `to_map_grid(..., like=...)` may ignore `like` when already projected. It is not a universal warp-to-reference call. Translation registration cannot resolve arbitrary detector deformation.

Sensor guides: [EMIT](emit.md), [PRISMA](prisma.md), [PACE](pace.md), [EnMAP](enmap.md), [DESIS](desis.md), [Tanager](tanager.md), [AVIRIS](aviris.md), [NEON](neon.md). Run `scripts/sensor_table.py` for installed support, then inspect actual data—not just a static table.
