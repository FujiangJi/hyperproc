# hyperproc.align._common_box

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _common_box(a: np.ndarray, b: np.ndarray) -> tuple
```

Slices of the smallest box containing every pixel finite in both.

Two scenes rarely cover exactly the same ground, and the part of the grid
only one of them reaches is NaN. Filling that with zeros leaves a hard step
in the middle of the array, and a step correlates with a step: the spurious
peak can beat the real one outright. Cropping both to their common box
removes it, and a crop applied equally to both cannot change the shift
between them.

[Module and aliases](../hyperproc-align.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.align._common_box --runtime`.
