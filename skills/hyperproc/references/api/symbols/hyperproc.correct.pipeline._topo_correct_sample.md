# hyperproc.correct.pipeline._topo_correct_sample

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _topo_correct_sample(s: Sample, tc: TopoCoefficients | None, wl: np.ndarray) -> np.ndarray
```

The sample's spectra topographically corrected with ``tc``, on the
sample's *own* wavelength axis (``wl`` must be ``s.wavelength``; a group
member's axis may differ from the first sample's by up to 1 nm, more than
the 0.5 nm coefficient alignment tolerates).

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline._topo_correct_sample --runtime`.
