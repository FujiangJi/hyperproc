# Processing decision guide

## First decide what you have

1. **Identify the physical quantity.** Read product-level and unit metadata, not only the variable name.
2. **Check geometry and quality.** Locate required sidecars and determine whether data are already mapped.
3. **Choose an input branch.** Surface reflectance normally bypasses atmospheric retrieval. Supported at-sensor inputs can enter the optional ISOFIT path.
4. **Choose surface corrections from evidence.** An available function is not a reason to apply it.
5. **Prepare the analysis grid and spectral support.** Align only when needed and document resampling.
6. **Calculate features and export provenance.** Verify the written output, not only an in-memory plot.

## Three typical routes

| Route | Sequence |
|---|---|
| Provider L2 reflectance → spectral features | Open → inspect → quality policy → optional spatial/spectral preparation → features → export |
| Airborne reflectance group → normalized windows | Open group → sample selected regions → per-line topo diagnostics → optional topo → grouped FlexBRDF → apply → seam/angle diagnostics → export |
| Supported L1 input → mapped reflectance | Open → prepare ISOFIT inputs → retrieve → optional satellite NBAR → map → export cube, retrieval layers, QA, and provenance |

## Corrections are not interchangeable

Atmospheric correction addresses atmospheric effects on the measurement. Topographic correction addresses illumination associated with terrain. BRDF normalization adjusts directional reflectance to a selected angular condition. Georeferencing addresses spatial placement. Smoothing changes spectral shape. None is a substitute for another.

The implemented high-level topographic/FlexBRDF pipeline is **airborne-only**. That implementation boundary must not be read as a scientific assertion that terrain does not affect satellite imagery. Similarly, the MCD43 route is the package's supported satellite strategy, not proof that all satellites lack useful angular diversity.

## Avoid automatic overcorrection

Provider products may already include corrections relevant to your target analysis. Inspect their processing documentation and your residual diagnostics. A topographic verdict of `skip`, `refuse`, or `inconclusive` is meaningful information. Do not convert all of those results into `force_topo=True` for convenience.

## Reproducible decisions

Keep input identifiers, processing region, sample strategy, masks, coefficients, solar reference, SRF source, interpolation choices, cache provenance, and dependency versions. If you transfer coefficients from provider reflectance to a new retrieval, label that transfer and validate it separately.
