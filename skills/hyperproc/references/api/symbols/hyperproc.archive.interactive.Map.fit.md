# hyperproc.archive.interactive.Map.fit

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fit(self) -> None
```

Centre and zoom on the footprints, or on the drawn box if there are none.

Sets ``center`` and ``zoom`` rather than only calling ``fit_bounds``:
those are traits, so they are saved with the notebook and the map opens
on the data when the file is reopened without a kernel. ``fit_bounds``
is still called, because a live browser refines the fit.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.Map.fit --runtime`.
