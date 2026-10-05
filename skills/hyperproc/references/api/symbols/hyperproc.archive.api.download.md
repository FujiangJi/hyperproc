# hyperproc.archive.api.download

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def download(results, out_dir: str | Path='data', workers: int=8, *, token: str | None=None, user: str | None=None, password: str | None=None, pattern: str | None=None, accept_policy: bool=False, verbose: bool=True) -> list[Path]
```

Fetch what a search found, from whichever archives it came from.

Args:
    results: a :class:`~hyperproc.archive.results.Results`, a list of
        granules, or one granule. A mixture of archives is fine; each group
        goes to its own backend.
    out_dir: created if missing. Everything lands flat, which is what the
        readers expect - they find a granule's siblings by name.
    workers: parallel connections.
    token: NEON API token, else ``NEON_TOKEN``.
    user, password: DLR EOC account, else ``DLR_EOC_USERNAME`` /
        ``DLR_EOC_PASSWORD``, else ``~/.netrc``.
    pattern: NEON only - which files inside a site-month delivery to take.
    accept_policy: DLR only - agree to its Acceptable Usage Policy from
        here. Left ``False``, a pending policy stops the download and says
        where to read it, because agreeing to it is yours to do.

Returns:
    the downloaded paths.

Credentials differ by archive and none of them are needed to search:
Earthdata for EMIT, PACE and AVIRIS; a NEON API token since June 2026; a
DLR EOC account for EnMAP and DESIS. Each backend raises with its own
registration address when it has none.

[Module and aliases](../hyperproc-archive-api.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.api.download --runtime`.
