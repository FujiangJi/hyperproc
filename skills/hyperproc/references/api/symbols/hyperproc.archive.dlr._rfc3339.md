# hyperproc.archive.dlr._rfc3339

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _rfc3339(date) -> str | None
```

``date=`` as a STAC ``datetime`` interval.

A bare day means the whole day, not midnight, which is the difference
between finding a scene and not.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr._rfc3339 --runtime`.
