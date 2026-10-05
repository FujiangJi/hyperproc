# hyperproc.align.apply_shift

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def apply_shift(ds: xr.Dataset, dy: float, dx: float, unit: str='pixel') -> xr.Dataset
```

Move a dataset's georeferencing by a shift, leaving the pixels untouched.

Args:
    ds: the dataset to move.
    dy, dx: how far its content must move, down and right.
    unit: ``"pixel"`` of this dataset, or ``"map"`` units of its CRS.

Returns:
    A copy with ``x``/``y`` coordinates and ``attrs["transform"]`` moved.
    Nothing is resampled, so this is exact and free.

[Module and aliases](../hyperproc-align.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.align.apply_shift --runtime`.
