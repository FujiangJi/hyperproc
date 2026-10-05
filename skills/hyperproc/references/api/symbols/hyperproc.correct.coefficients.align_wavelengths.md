# hyperproc.correct.coefficients.align_wavelengths

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def align_wavelengths(have: np.ndarray, want: np.ndarray, tol: float=0.5) -> np.ndarray
```

Index into ``have`` for each wavelength in ``want`` (nearest within
``tol`` nm), -1 where none is close enough.

[Module and aliases](../hyperproc-correct-coefficients.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.coefficients.align_wavelengths --runtime`.
