# hyperproc.archive.dlr._page_says

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _page_says(html: str) -> str
```

The sign-on's own message, so a refusal states its actual reason.

"Authentication attempt has failed" and "Your account is locked" arrive
with the same HTTP status, and only one of them means the password was
wrong.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr._page_says --runtime`.
