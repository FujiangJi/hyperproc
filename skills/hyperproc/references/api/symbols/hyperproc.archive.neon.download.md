# hyperproc.archive.neon.download

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def download(results, out_dir: str | Path='data', workers: int=4, token: str | None=None, pattern: str | None=None, verbose: bool=True) -> list[Path]
```

Fetch NEON files into ``out_dir``. NEON requires a token for this.

Deliveries are expanded to their files first, so passing what
:func:`search` returned downloads a whole site-month - often hundreds of
gigabytes. The total is printed before anything is fetched; narrow it with
:func:`files` and a slice, or with ``pattern=``.

[Module and aliases](../hyperproc-archive-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.neon.download --runtime`.
