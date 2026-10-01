# Testing and reproducibility

## Package test suite

The checkout contains pytest tests alongside executed tutorial notebooks. The suite covers readers, correction, geometry, quality, spectral operations, alignment, atmospheric configuration, and archive access. Install and run from the repository root:

```bash
pip install -e '.[test]'
pytest
pytest -m "not data and not network"  # no private granules or live archives
pytest -m data                     # needs tests/data provider granules
pytest -m network                  # explicitly queries live archives
```

Optional capabilities may need their extras in the test environment. The package README records suite counts and run evidence; the documentation build does not rerun those tests or certify their scientific results.

## Evidence by layer

- Analytic/synthetic tests check known derivatives, kernels, resampling identities, bit flags, and planted alignment shifts.
- Reader tests check recorded metadata fingerprints and physical invariants against provisioned granules.
- The R-compatible spline route uses retained reference spectra/results from R.
- Archive tests replay fixtures from CMR, NEON, and DLR and test map state without requiring live queries. `tests/tools/make_archive_fixtures.py` refreshes recordings; review their changes.
- Tests marked `network` check live archive behavior separately, including sign-on assumptions.
- Saved notebook outputs document historical examples; they are not fresh regression-test results.

Independent scientific benchmarks and a complete dependency/platform CI matrix require separate evidence. Keep imagery, credentials, large downloads, and full retrievals out of routine offline CI.

## Reproducibility record

Keep code revision, input identifiers/hashes, environment, parameters, random seed, sample region, cache state, coefficient files, runtime/memory, and diagnostics. Identify fitting versus evaluation pixels/flightlines and whether a retrieval was reused.

## Documentation checks

The site has its own strict build and integrity checks for links, fragments, assets, API definitions, notebook copies, and package/metadata source hashes. These verify documentation integrity; they do not execute package algorithms.
