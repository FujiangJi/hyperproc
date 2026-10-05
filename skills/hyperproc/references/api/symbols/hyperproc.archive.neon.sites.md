# hyperproc.archive.neon.sites

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def sites(refresh: bool=False) -> dict[str, dict]
```

Every NEON site, keyed by code, with coordinates and what was flown there.

One anonymous call answers both halves of a search, which is why the module
uses it rather than ``/products``: each site carries ``siteLatitude``,
``siteLongitude`` and a ``dataProducts`` list whose entries name the months
available. Cached for the process.

[Module and aliases](../hyperproc-archive-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.neon.sites --runtime`.
