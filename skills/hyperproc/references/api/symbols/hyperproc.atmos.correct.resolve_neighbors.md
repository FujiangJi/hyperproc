# hyperproc.atmos.correct.resolve_neighbors

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def resolve_neighbors(inputs: Inputs, segmentation_size: int, num_neighbors=None) -> list
```

Neighbour count per atmospheric term, in the order the analytical line wants.

``num_neighbors`` may be a dict keyed by term, a single number for every
term, or a sequence matching :func:`atm_terms`; None uses
:data:`ATM_NEIGHBORS`. Every value is capped by :func:`neighbor_cap`.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.resolve_neighbors --runtime`.
