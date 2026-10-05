# hyperproc.archive.interactive.Map.show

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def show(self, results, fit: bool=True)
```

Draw a result set you already have, without searching again.

Args:
    results: a :class:`~hyperproc.archive.results.Results`, or a list
        of granules.
    fit: zoom to the footprints. ``False`` leaves the view alone.

Returns the results, so it chains.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.Map.show --runtime`.
