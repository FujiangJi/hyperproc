# hyperproc.atmos.correct._clean_partial

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _clean_partial(inputs: Inputs) -> None
```

Remove what an interrupted or failed run left half-written.

ISOFIT creates its output files before filling them and, on resume,
trusts any file that exists (a presolve file from a run that died in the
engine constructor was taken as "existing h2o-presolve solutions"). So
everything under ``output/`` goes, together with the assembled
``lut.zarr`` stores. The raw radiative-transfer simulations beside them
(6S ``LUT_*`` files, libRadtran ``*.out``), which are the expensive part,
stay: every engine skips simulations whose files already exist.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct._clean_partial --runtime`.
