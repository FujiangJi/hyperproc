# hyperproc.atmos.correct.run_isofit

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def run_isofit(inputs: Inputs, command: list[str], timeout: float | None=None, verbose: bool=True) -> dict
```

Run ``command`` (from :func:`build_command`), blocking, with logs in the work dir.

Returns a record (command, start, end, seconds, returncode, isofit version)
that is also written to ``<work_dir>/hyperproc_ac.json``. Raises
RuntimeError with the tail of the log when ISOFIT exits non-zero or
leaves no reflectance file.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.run_isofit --runtime`.
