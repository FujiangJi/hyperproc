# Airborne surface reflectance → evidence-gated normalized reflectance

This released high-level route targets NEON and AVIRIS families. It is not a universal satellite terrain/BRDF pipeline. Confirm geometry conventions, calibrated reflectance, masks, compatible spectra and representative flightline group.

1. Select scientifically compatible flightlines and fitting population. Multiple chunks of one flightline do not create independent view-angle acquisitions.
2. Sample representative terrain/land-cover and across-track angles; record region, seed, masks and eligibility. Pixel sampling can read the entire supplied region for topo statistics despite a small fraction/cap.
3. Fit topo per appropriate flightline and read full diagnostic/valid bands. Verdicts are `correct`, `skip`, `refuse`, `inconclusive`—not `applied`. Keep normal gates; force only a user-requested, labeled experiment.
4. Fit grouped BRDF on the same preceding correction state intended for application, with angular/conditioning support and target-sun choices.
5. Apply/export only warranted stages and evaluate held-out locations/lines, wavelength/class residuals, seams, spectral artifacts and unchanged/BRDF-only baselines.

```python
import hyperproc as hp
import hyperproc.correct as hc

paths = ["/data/actual_flightline_1", "/data/actual_flightline_2"]
datasets = [hp.open(path) for path in paths]
samples = [hc.sample_image(ds, fraction=0.1, max_pixels=250_000,
                           strategy="pixels", seed=0) for ds in datasets]
topos = [hc.fit_topo(sample, method="scs+c", fit="nnls") for sample in samples]
for coefficients in topos:
    print(coefficients.verdict, coefficients.n_ok)
# Inspect gates/diagnostics and scientific applicability before these steps.
brdf = hc.fit_brdf(samples, topo=topos, group_id="actual-compatible-group")
corrected = hc.apply(datasets[0], topo=topos[0], brdf=brdf)
hc.export(corrected, "/work/corrected-group", window=(600, 800, 600, 800))
```

This sampling example uses each whole supplied dataset; for large scenes define/justify representative fitting regions first. Close datasets after computation/export completes. `apply` is lazy; export actually performs work. Do not report graph construction as completed processing.

For BRDF-only, fit a separate model with `topo=None`; do not apply a model trained after topo as if it used uncorrected spectra. `merge_samples` is for a justified sample-level grouping; preserve physical flightline identity/per-line topo decisions. Cross-retrieval coefficient transfer requires its own disclosure/evaluation.

Keep coefficient JSON, eligibility/apply masks, group/solar reference, band order, diagnostic verdicts and geometry provenance. Overlap improvements involving training lines are not independent validation; report wavelengths/classes that worsen as well. See [advanced corrections](advanced-corrections.md) and [science readiness](science-ready.md).
