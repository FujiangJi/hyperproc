# hyperproc.correct.kernels._li_terms

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _li_terms(sza, vza, raa, b_r, h_b)
```

The shared pieces of every Li kernel, Wanner et al. 1995 eqs 43-47.

The crown shape enters twice: ``b_r`` rescales both zenith angles to the
equivalent spherical-crown geometry (eq 47), ``h_b`` sets the height at
which the two shadows overlap (eq 44). ``cos t`` is clipped to [-1, 1] -
beyond that the shadows do not overlap at all and the overlap term is 0.

[Module and aliases](../hyperproc-correct-kernels.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.kernels._li_terms --runtime`.
