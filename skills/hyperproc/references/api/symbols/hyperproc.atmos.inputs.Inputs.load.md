# hyperproc.atmos.inputs.Inputs.load

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def load(cls, work_dir: str | Path) -> 'Inputs'
```

Decorators: `classmethod`.

Read ``<work_dir>/input/inputs.json``, rebased onto ``work_dir``.

The file stores absolute paths, so a work directory that was moved or
copied would otherwise point every read back at the original and two
different runs would silently return the same products.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs.Inputs.load --runtime`.
