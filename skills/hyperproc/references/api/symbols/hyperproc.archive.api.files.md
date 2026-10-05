# hyperproc.archive.api.files

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def files(results, **kwargs) -> Results
```

Open a NEON site-month delivery up into the flightlines inside it.

For CMR and DLR a granule already *is* its files - the links are on it - so
this returns what it was given, unchanged. That way one script works
against every archive.

See :func:`hyperproc.archive.neon.files` for ``token=`` and ``pattern=``.

[Module and aliases](../hyperproc-archive-api.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.api.files --runtime`.
