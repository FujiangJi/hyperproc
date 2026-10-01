# Airborne topographic and BRDF correction

The high-level pipeline targets NEON and the AVIRIS family. It separates **sampling**, **fitting**, **applying**, and **exporting** so coefficients and diagnostics can be inspected before imagery is changed.

## 1. Select an appropriate flightline group

Use compatible sensor wavelengths, acquisition conditions, and surface populations. Multiple files from the same physical flightline do not automatically provide independent angular sampling. AVIRIS-5 chunks may need to be merged at the sample level before fitting one topographic model per flightline.

## 2. Define the fitting population

```python
import hyperproc as hp
import hyperproc.correct as hc

paths = ["/path/to/flightline_1", "/path/to/flightline_2"]
datasets = [hp.open(path) for path in paths]
samples = [hc.sample_image(ds, fraction=0.1, max_pixels=250_000,
                           strategy="pixels", seed=0)
           for ds in datasets]
```

This example samples **whole supplied datasets**. If you first select 2,000 rows, the sample and diagnostics describe those rows. Preserve across-track coverage for angular diversity, but assess whether reduced along-track extent remains representative of terrain and land cover.

With `strategy="pixels"`, the implementation reads the supplied region to build masks and collect topographic regression sums over eligible pixels, while subsampling for BRDF. `strategy="chunks"` is an approximate lower-I/O alternative. Fraction and cap do not mean that all stages use the same number of observations.

## 3. Fit and inspect topographic coefficients

```python
topos = [hc.fit_topo(sample, method="scs+c", fit="nnls") for sample in samples]
for coefficients in topos:
    print(coefficients.verdict, coefficients.n_ok)
    coefficients.to_json("products/coefficients")
```

The SCS+C multiplier is `(cos(slope) × cos(sza) + C) / (cos_i + C)`, with fitted `C` by band. Available low-level methods also include cosine, C, and SCS. The illumination diagnostic examines residual relationships and spatial consistency; it is not simply a terrain-slope threshold.

| Verdict | Operational interpretation |
|---|---|
| `correct` | Diagnostic supports applying the correction under its assumptions |
| `skip` | Evidence does not support the need to correct |
| `refuse` | The fitted behavior is unsuitable for the proposed correction |
| `inconclusive` | Available evidence is insufficient for a confident decision |

Use the complete diagnostic, not only its label. Leave `force_topo=False` for the normal evidence-gated route. An unavailable per-band `C` is not repaired by forcing the global verdict.

## 4. Fit grouped FlexBRDF

```python
brdf = hc.fit_brdf(samples, topo=topos, group_id="flight-group")
print(brdf.summary())
brdf.to_json("products/coefficients")
```

The implementation uses RossThick/LiDenseReciprocal kernels by default, NDVI-stratified fitting, and a group solar reference. Angular diversity is screened using robust view-zenith span and design-matrix conditioning. Passing that gate establishes numerical support for the fit, not guaranteed scientific improvement.

If comparing BRDF-only against topo→BRDF, fit a separate model with `topo=None` for the BRDF-only branch. Do not apply a model fitted after topographic correction as if it were fitted to unchanged spectra.

## 5. Apply, export, and evaluate

```python
corrected = hc.apply(datasets[0], topo=topos[0], brdf=brdf)
hc.export(corrected, "products/corrected", window=(3000, 3500, 400, 900))
```

`apply()` is lazy. Export triggers computation. It already updates stage-related naming; adding the same suffix again can produce duplicate stage names.

Evaluate angular dependence, overlap agreement, spectral discontinuities, spatial artifacts, and effects by land-cover/NDVI class. Hold out flightlines or locations where possible. An overlap comparison involving training imagery is useful but not automatically an independent test.

Scientific basis: [Queally et al., FlexBRDF](https://doi.org/10.1029/2021JG006622). See [pipeline API](../api/hyperproc-correct-pipeline.md) and the [curated AVIRIS-3 walkthrough](../tutorials/aviris3-walkthrough.md).
