# hyperproc.archive.cmr._browse_of

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _browse_of(umm: dict) -> str | None
```

A quicklook a browser can load, or ``None``.

CMR lists the same image twice, once over https and once as an ``s3://``
URI that nothing outside AWS can open, so only the https one is any use on
a map. Some collections list a browse that was never written - PACE's all
404 - which is a property of the archive, not something to paper over.

[Module and aliases](../hyperproc-archive-cmr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.cmr._browse_of --runtime`.
