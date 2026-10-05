# hyperproc.correct.topo.correction_factor

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def correction_factor(method, cos_i, sza, slope=None, c=None)
```

The multiplicative factor for one of :data:`METHODS`. Radians in, factor out.

``c`` may be a scalar or an array broadcastable against ``cos_i`` (one C per
band, with a trailing band axis, is the usual case).

[Module and aliases](../hyperproc-correct-topo.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.topo.correction_factor --runtime`.
