# hyperproc.archive.api.can_download

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def can_download(sensor: str, level: str | None=None) -> bool
```

Could this process fetch bytes for this collection, as things stand?

Answers the question :func:`download` would otherwise answer by failing.
Says nothing about whether the account is *cleared* for the data - only
DLR can say that, and only when asked.

[Module and aliases](../hyperproc-archive-api.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.api.can_download --runtime`.
