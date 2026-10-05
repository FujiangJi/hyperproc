# hyperproc.correct.mcd43.date_of

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def date_of(source) -> str
```

The acquisition date as ``YYYY-MM-DD``.

Args:
    source: an open dataset, or a granule path or file name. A dataset's
        ``datetime`` attribute wins; otherwise the first eight-digit date
        in the granule name is used, which every sensor in the package
        puts there.

Raises:
    ValueError: nothing in the name or the attributes looks like a date.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.date_of --runtime`.
