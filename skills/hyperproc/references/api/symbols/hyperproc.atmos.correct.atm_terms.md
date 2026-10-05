# hyperproc.atmos.correct.atm_terms

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def atm_terms(inputs: Inputs) -> list
```

Atmospheric terms the analytical line interpolates, in ISOFIT's order.

Taken from a previous run's products where there is one (the interpolated
atmosphere file names its bands), otherwise the two terms every retrieval
has. Instrument terms in the state vector (EMIT's EOFs) are not
interpolated and are left out.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.atm_terms --runtime`.
