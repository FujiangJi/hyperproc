# hyperproc.archive.dlr._content_range

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _content_range(r) -> tuple[int | None, int | None]
```

``(first byte, total size)`` from a 206 or 416 answer, None where absent.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr._content_range --runtime`.
