## Airborne topographic/FlexBRDF branch

The released high-level pipeline targets NEON and AVIRIS families. Confirm `is_airborne`, reliable geometry conventions, reflectance, eligible masks, and sample representativeness. Do not use the pipeline merely because any dataset contains view angles.

### Sampling and grouping

`sample_image(ds, fraction=..., max_pixels=..., strategy=..., seed=...)` separates fitting support from later application. `strategy="pixels"` reads the supplied region for masks/topographic sufficient statistics while subsampling BRDF; fraction/cap do not bound every stage to the same sample count. `strategy="chunks"` trades approximation for lower I/O. Use `merge_samples` for compatible chunks of one physical flightline where justified; files/chunks are not automatically independent angle acquisitions.

Keep sufficient across-track angular span and representative along-track terrain/land-cover populations. Describe exact region/seed/masks, bands and source identity. A fast narrow window can be an initial test but not establish flightline-wide coefficients. Inspect `angular_diversity` and `per_block_effects` where needed.

### Topographic fit and gates

`fit_topo` produces wavelength-keyed coefficients/diagnostics. SCS+C uses `(cos(slope)*cos(sza)+C)/(cos_i+C)`; C is fitted by band. Other low-level methods include cosine, C and SCS. Inspect fit method/usable samples, per-band C validity, terrain/illumination residuals and verdict. `correct` supports application under assumptions; `skip` lacks evidence of need; `refuse` unsuitable fit; `inconclusive` insufficient evidence. Leave normal `force_topo=False` unless explicitly executing a labeled experiment. A forced global verdict does not repair unavailable band coefficients.

### Group BRDF fit

`fit_brdf(samples, topo=topos, group_id=...)` pools compatible samples with the intended preceding correction. Default kernels RossThick/LiDenseReciprocal and NDVI strata/solar reference need scientific interpretation. Robust view-zenith span/design conditioning screen numerical support. Poor conditioning is not cured by grouping arbitrary unrelated scenes. `brdf.summary()` and coefficient JSON expose diagnostics/provenance.

For BRDF-only comparison, fit another model with `topo=None`. A BRDF model fitted to topo-corrected spectra must not be applied to unchanged spectra as if it were the same experiment. If transferring coefficients across a new atmospheric retrieval, document that transfer and validate separately.

### Apply and export

`hc.apply` is lazy; `hc.export` computes/writes output and provenance. Application updates naming/stage metadata; do not append duplicate stage suffixes. Check bounds/window interpretation and avoid unintentional overwrite. Inspect seams, spectra, NDVI-class residuals, angular dependence and held-out overlap agreement. An overlap involving training flightlines is not an independent test. Document improvements and degradations by wavelength rather than selecting favorable bands.

References: [airborne workflow](https://fujiangji.github.io/hyperproc/workflows/airborne/), [pipeline](../api/hyperproc-correct-pipeline.md), [topo](../api/hyperproc-correct-topo.md), [BRDF](../api/hyperproc-correct-brdf.md), [masks](../api/hyperproc-correct-masks.md), [coefficient classes](../api/hyperproc-correct-coefficients.md), [kernels](../api/hyperproc-correct-kernels.md). `TopoCoefficients`, `BRDFCoefficients`, and `load` preserve wavelength-keyed records; inspect serialization/application support before changing wavelengths. Low-level kernels generally accept radians. Do not feed reader degree arrays unchanged.
