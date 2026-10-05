# hyperproc.correct.mcd43.Params.masked

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def masked(self, qa_max: int | None=3, snow: bool=True) -> 'Params'
```

A copy with low-quality and (optionally) snow-covered cells set to NaN.

Args:
    qa_max: keep cells whose band quality is <= this. The default 3
        keeps every retrieval, including magnitude inversions. That is
        deliberate: a magnitude inversion scales an archetype shape to
        the observed brightness, and a common factor on all three
        weights cancels in the c-factor ratio, so it costs far less
        here than it would in an albedo. Dropping them instead leaves
        holes that make neighbouring pixels inconsistent. Pass 1 for
        full inversions only; None keeps every cell including fill.
    snow: drop cells flagged as snow-covered. A snow BRDF is a real
        measurement, but the surface it describes is usually gone by
        the time a different sensor sees it.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.Params.masked --runtime`.
