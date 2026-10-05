# hyperproc.atmos.correct.redo_line

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def redo_line(inputs: Inputs, verbose: bool=True) -> None
```

Drop only what the analytical line produced, keeping the retrieval.

The look-up tables, the segmentation and the superpixel inversions are the
expensive part and do not depend on how the atmospheric state is
interpolated, so tuning ``num_neighbors`` costs only the last stage
(27 of 51 minutes on the EMIT test granule).

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.redo_line --runtime`.
