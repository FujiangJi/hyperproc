# hyperproc.archive.interactive.Map.download

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def download(self, out_dir: str | None=None, **kwargs)
```

Download the selected granules. Same as ``hp.download(m.selected, ...)``.

Credentials come from the environment exactly as they do there; nothing
is typed into the map.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.Map.download --runtime`.
