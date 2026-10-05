# hyperproc.archive.interactive.Map.search

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def search(self, sensor: str | None=None, level: str | None=None, **kwargs)
```

Search the drawn box. With no arguments, uses the panel's settings.

Returns the :class:`~hyperproc.archive.results.Results`, and draws the
footprints on the map.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.Map.search --runtime`.
