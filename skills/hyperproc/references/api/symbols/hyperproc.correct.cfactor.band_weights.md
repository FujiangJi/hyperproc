# hyperproc.correct.cfactor.band_weights

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def band_weights(wavelength, mode: str='interp') -> np.ndarray
```

``(7, nwl)`` weights that turn seven MODIS c-factors into per-band ones.

Args:
    wavelength: instrument band centres in nm.
    mode: ``"interp"`` for linear interpolation between the MODIS band
        centres (constant outside them), ``"nearest"`` for the one-hot
        closest-band assignment of :func:`band_map`.

Returns:
    A matrix whose columns sum to 1, so it is an average of the seven
    c-factors and never changes their scale.

[Module and aliases](../hyperproc-correct-cfactor.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.cfactor.band_weights --runtime`.
