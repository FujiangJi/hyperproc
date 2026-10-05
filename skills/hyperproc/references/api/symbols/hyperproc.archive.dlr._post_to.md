# hyperproc.archive.dlr._post_to

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _post_to(page_url: str, action: str | None) -> str
```

Where a form submits to.

An empty or self-referential ``action`` posts back to the page *including
its query string*, which is where CAS keeps the ``service`` it is signing
you in to. ``urljoin`` would drop it.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr._post_to --runtime`.
