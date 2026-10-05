## Build, inspect, apply, preserve

`hp.quality_flags` aliases `quality.build`; `hp.quality_apply` aliases `quality.apply`. Building the uint16 bitfield reports conditions; masking changes only the selected cube variable under the selected drop policy. Preserve original provider masks and the QA field used in analysis. The default drop set is fill, cloud, cloud_shadow, cirrus. Water and snow are scientific choices, not automatic generic rejects.

Bits: 0 fill; 1 saturated; 2 cloud; 3 cloud_shadow; 4 cirrus; 5 snow_ice; 6 water; 7 haze; 8 sun_glint; 9 terrain_shadow; 10 steep_terrain; 11 ac_failed; 12 brdf_filled; 13 negative_reflectance. Bits 14–15 are reserved in this release. Multiple bits may coexist. Default derived flags are fill and terrain_shadow; optional negative-reflectance/steep-terrain/spectral-cloud behavior must be chosen/read from exact signatures.

Decode selected flags with `quality.decode`. Use `quality.describe`/`hp.quality_table` for meanings and `quality.summary`/`hp.quality_summary` for counts. Verify actual return types; do not assume a printing function returns a table. If using `set_flag`, follow its mutation behavior/signature. Boolean provider masks and coded classification layers are separate sources; preserve source provenance. Land is not always simply the inverse of a provider water label. BRDF-valid codes distinguish retrieved, filled, and missing-observation conditions.

QA absence is not clear-sky certification. A derived fill mask may require reading spectral values, and building a mask over a whole dataset can perform full-region I/O. Build QA on the scientifically appropriate region and retain which inputs were actually available. Integer masks and QA overviews require categorical-safe resampling.
