## Indices and absorption metrics

`hp.spectral_index(ds, "NDVI")` resolves `features.index`, not an arbitrary evaluation of Python. Named indices are NDVI, EVI, NDWI, NDII, PRI, NDNI, CAI, MCARI, ARI1, CRI1, PSRI, NDSI. Read each exact formula and citation in `features.INDICES`/`describe_indices`. This release's NDVI uses 860 and 660 nm. Named NDWI uses 860 and 1240 nm (Gao), which differs from other formulas called NDWI.

A custom formula uses tokens such as `R800` and `R670`; restricted arithmetic and log/log10/sqrt/exp/abs are available. Actual bands used are stored in result attributes. Formula validity does not establish physical validity on radiance or scaled integers. Ratios near zero denominators and log-domain violations require checking; do not silently clip values to hide the issue.

`hp.band_depth` returns depth, position and area for a named/custom window. Named windows are chlorophyll (550–750), water_970 (900–1050), water_1200 (1100–1300), lignin_1730 (1650–1850), cellulose (2000–2300), clay_2200 (2100–2300), all nm. Confirm measured support and usable shoulders before using the metric. These are descriptors, not calibrated concentrations. Compare unsmoothed baselines; smoothing/gap filling can bias narrow features. SWIR features are unavailable for DESIS regardless of shared interface.
