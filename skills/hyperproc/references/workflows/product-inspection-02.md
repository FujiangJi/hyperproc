## Supported product distinctions

| Sensor | Implemented registry levels | Interpretation / essential caution |
|---|---|---|
| EMIT | L1B, L2A | RAD radiance versus RFL reflectance; use matched OBS/MASK and GLT pathway when needed |
| PRISMA | L1, L2B, L2C, L2D | L1 at-sensor radiance; L2B **at-surface radiance**; L2C swath surface reflectance; L2D mapped reflectance |
| EnMAP | L1B, L1C, L2A | L1B VNIR/SWIR are separate, unregistered detector cubes; select `cube`; L1C mapped radiance, L2A mapped reflectance; `_COG` names recognized |
| DESIS | L1B, L1C, L2A | VNIR-only; L1B sensor-grid radiance, L1C mapped radiance, L2A reflectance; cannot supply SWIR features |
| PACE OCI | L1B, L2 | L1B TOA reflectance through dedicated conversion when atmospheric input is needed; L2 supported SFREFL, not arbitrary ocean-color NetCDF |
| Tanager | L1B, L2A | Ortho radiance / surface reflectance HDF5; retain calibrated units and metadata |
| AVIRIS Classic/NG/3/5 | L1B, L2A | Variant-specific ENVI/NetCDF, geometry and gain sidecars; generic AVIRIS can infer variant; directories can be discovered |
| NEON | L1 (DP1) | DP1.30006.001 flightline **surface reflectance**, not L1 at-sensor radiance |
| NEON DP3 | L3 registry entry | Planned, not implemented; raise/stop instead of pretending support |

HISUI, Hyperion, GF-5/AHSI and absent registry families have no released reader route. Registry keys include generic AVIRIS and instrument aliases; their presence is not distinct scientific validation for each combination. Reader support and archive search support are separate.
