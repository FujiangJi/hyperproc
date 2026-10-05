## Transform choices

| Operation | Released entry point | Decision and output caveat |
|---|---|---|
| Savitzky–Golay/moving smoothing | `hp.smooth_spectra` | Window/order/method appropriate to spacing and feature width; good runs, restore NaNs, altered shape |
| Spike diagnosis | `hp.find_spikes` | Diagnostic flags require review; not proof every spike is instrumental |
| Spline/gap filling | `hp.spline_gapfill` | PRISMA-oriented default masks; `spline_filled` marks synthesized samples; avoid inventing absorption measurements |
| Continuum removal | `hp.continuum_removal` | Interval defines shoulders/hull; gaps/noise affect depth; output no longer physical reflectance |
| Derivative | `hp.spectral_derivative` / `spectral.derivative` | Polynomial/window/order and representative spacing; derivative units per wavelength; check irregular sampling |
| Spectral response/grid matching | `hp.resample` | Explicit wavelengths/FWHM, like, step or sensor choices; spectral support not spatial resolution |

See [smoothing](../api/hyperproc-spectral-smoothing.md), [continuum](../api/hyperproc-spectral-continuum.md), [derivatives](../api/hyperproc-spectral-derivatives.md), and [bands](../api/hyperproc-spectral-bands.md). Internal `_smoothspline` is fully catalogued for debugging but exported spline APIs are preferred.
