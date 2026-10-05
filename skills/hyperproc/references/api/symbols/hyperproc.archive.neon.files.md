# hyperproc.archive.neon.files

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def files(results, *, token: str | None=None, pattern: str | None=None, verbose: bool=True) -> Results
```

List the files inside one or more deliveries.

NEON has required a token for this since June 2026. One is sent when there
is one; the request goes out either way, and a refusal comes back as a
:class:`PermissionError` quoting the address a token comes from.

Args:
    results: what :func:`search` returned, a list of deliveries, or one.
    token: the NEON API token. Defaults to ``NEON_TOKEN``.
    pattern: a shell glob over file names. The default keeps only what
        :func:`hyperproc.open` reads - ``*_reflectance.h5`` for
        DP1.30006.001 - because a delivery also carries flight logs,
        reports and quicklooks. ``"*"`` keeps everything.
    verbose: print what was found.

Returns:
    :class:`Results`, one granule per file, with a real size and a link.

The links NEON returns are signed and expire within the hour, so list and
download in one sitting rather than pickling the result.

[Module and aliases](../hyperproc-archive-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.neon.files --runtime`.
