# hyperproc.correct.masks.range_mask

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def range_mask(layer, lo=-np.inf, hi=np.inf)
```

True where a layer lies within ``[lo, hi]`` and is finite.

``np.radians(5)`` on a slope layer, ``0.12`` on cos i, ``np.radians(2)`` on
the view zenith are the values EnSpec used for NEON.

[Module and aliases](../hyperproc-correct-masks.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.masks.range_mask --runtime`.
