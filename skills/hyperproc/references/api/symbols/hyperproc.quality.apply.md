# hyperproc.quality.apply

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def apply(ds: xr.Dataset, quality: xr.DataArray | None=None, drop: tuple[str, ...]=DEFAULT_DROP, var: str | None=None, keep: bool=True, derive: tuple[str, ...]=('fill',)) -> xr.Dataset
```

Set the cube to NaN wherever a dropped flag is set.

Args:
    ds: the dataset to mask.
    quality: a layer from :func:`build`; built here when omitted.
    drop: the flags to mask on. The default is the set almost no analysis
        wants: fill, cloud, cloud shadow and cirrus.
    var: the cube to mask; the main one by default.
    keep: attach the quality layer to the result as ``quality``.
    derive: passed to :func:`build` when ``quality`` is not given. The
        default derives only ``fill``, the one flag in ``DEFAULT_DROP``
        that no provider layer supplies directly.

Returns:
    A copy of ``ds``, lazy where ``ds`` was lazy.

[Module and aliases](../hyperproc-quality.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.quality.apply --runtime`.
