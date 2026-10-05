# hyperproc.spectral.resampling._weights_box

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _weights_box(s_wl, s_fw, t_wl, t_fw) -> np.ndarray
```

Source band as a rectangle, target as a Gaussian, integrated over the overlap.

The formulation used by Spectral Python's ``BandResampler``.

[Module and aliases](../hyperproc-spectral-resampling.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.resampling._weights_box --runtime`.
