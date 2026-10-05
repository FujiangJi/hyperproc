# hyperproc.correct.masks.sample_indices

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def sample_indices(mask, fraction=0.1, max_samples=None, seed=0)
```

Random flat indices of True pixels - ``fraction`` of them, capped.

The cap keeps a 20-line group from producing a hundred-million-row
regression for no gain in the coefficients.

[Module and aliases](../hyperproc-correct-masks.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.masks.sample_indices --runtime`.
