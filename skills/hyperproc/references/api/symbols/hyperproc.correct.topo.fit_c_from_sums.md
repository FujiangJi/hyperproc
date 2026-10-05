# hyperproc.correct.topo.fit_c_from_sums

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fit_c_from_sums(n, sx, sy, sxy, sxx, syy, cos_i_p05, cos_i_p95, method='ols', min_samples=100, min_spread=0.02, neg_tol=0.05)
```

:func:`fit_c` from per-band regression sums over *all* masked pixels of an
image, accumulated while the cube streams past - so the topographic C is
fitted on every pixel of the calc mask without holding the cube in memory.

``n, sx, sy, sxy, sxx, syy`` are the counts and sums of cos i (x) and
reflectance (y) over the mask; ``cos_i_p05/p95`` the illumination range
the effect size is expressed over. With two parameters the NNLS solution
is exact in closed form: the unconstrained fit when both coefficients are
non-negative, otherwise the better of the two boundary fits (b = 0 or a = 0).
Statuses are the same as :func:`fit_c`.

[Module and aliases](../hyperproc-correct-topo.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.topo.fit_c_from_sums --runtime`.
