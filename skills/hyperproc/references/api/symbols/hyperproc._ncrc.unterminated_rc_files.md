# hyperproc._ncrc.unterminated_rc_files

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def unterminated_rc_files(*dirs) -> list[Path]
```

Those of :data:`NC_RC_NAMES` in ``dirs`` whose last byte is not a newline.

``dirs`` defaults to the home directory. An empty file is fine - there is
no last line to run off the end of. Unreadable paths are skipped: this is
a diagnostic, and it must never be the thing that fails.

[Module and aliases](../hyperproc-_ncrc.md). For another installed version, use `scripts/api_index.py --symbol hyperproc._ncrc.unterminated_rc_files --runtime`.
