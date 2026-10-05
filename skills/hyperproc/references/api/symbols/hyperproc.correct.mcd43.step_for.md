# hyperproc.correct.mcd43.step_for

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def step_for(ds=None, res: float | None=None) -> tuple
```

Resolve the MODIS grid step to use, as ``(res, k)``.

``k`` is how many native MODIS cells go into one output cell, so ``k = 1``
means the product's own grid and ``k > 1`` means an aggregation.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.step_for --runtime`.
