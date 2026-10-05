# hyperproc.archive.api.credentials

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def credentials() -> dict[str, bool]
```

Which archives this process could download from. Never returns a secret.

The DLR entries are **per mission**, because DLR grants EnMAP and DESIS
separately and an account for one need not open the other. A single
"have I got DLR credentials" flag reads True when you hold only one of
them, and then waves the other through to a refusal.

    >>> hp.archive.credentials()
    {'cmr': True, 'neon': False, 'ENMAP': False, 'DESIS': True}

[Module and aliases](../hyperproc-archive-api.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.api.credentials --runtime`.
