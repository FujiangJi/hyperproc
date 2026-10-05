# hyperproc.spectral.derivatives.derivative

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def derivative(ds: xr.Dataset, var: str | None=None, order: int=1, window: int=7, poly: int=2, good_only: bool=True) -> xr.Dataset
```

The spectral derivative, by Savitzky-Golay.

Differentiating raw reflectance amplifies noise, so the derivative is taken
from a local polynomial fit instead of finite differences, and only inside
runs of usable bands: a difference taken across a water-vapour gap is an
artefact of the gap.

Args:
    ds: dataset with a ``(y, x, wavelength)`` cube.
    var: variable name; the main cube by default.
    order: 1 for the first derivative, 2 for the second.
    window: filter length in bands, odd and greater than ``poly``.
    poly: polynomial order of the local fit.
    good_only: differentiate only within runs of usable bands.

Returns:
    A copy of ``ds`` whose cube is d^order(reflectance)/d(wavelength)^order,
    per nm to that power.

Raises:
    ValueError: the window is even, too short, or no run is long enough.

[Module and aliases](../hyperproc-spectral-derivatives.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.derivatives.derivative --runtime`.
