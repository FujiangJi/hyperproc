# hyperproc.atmos.inputs.match_bands

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def match_bands(wl: np.ndarray, grid: np.ndarray, tol: float=2.0) -> list
```

Positions in ``wl`` nearest to each wavelength of ``grid``.

Raises when a grid band has no match within ``tol`` nm or two grid bands
claim the same one, which would mean the product is not the instrument
the grid describes.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs.match_bands --runtime`.
