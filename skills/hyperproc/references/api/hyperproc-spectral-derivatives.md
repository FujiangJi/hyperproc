# hyperproc.spectral.derivatives

Release baseline **0.1.2**; source `hyperproc/spectral/derivatives.py`. Choose a callable below rather than loading every declaration.

Spectral derivatives, by Savitzky-Golay.

Differentiating raw reflectance amplifies noise, so the derivative comes from a
local polynomial fit rather than finite differences, and only inside runs of
usable bands: a difference taken across a water-vapour gap measures the gap.

## Declared exports

`derivative`

## Imported aliases

- `main_var` → `hyperproc.io.main_var`
- `good_bands` → `hyperproc.spectral.bands.good_bands`
- `_runs` → `hyperproc.spectral.bands.runs_of_good_bands`

## Declared callables and classes

- [_derivative_block](symbols/hyperproc.spectral.derivatives._derivative_block.md) — internal
- [derivative](symbols/hyperproc.spectral.derivatives.derivative.md)
