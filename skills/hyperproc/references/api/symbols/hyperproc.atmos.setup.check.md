# hyperproc.atmos.setup.check

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def check(engines=('sRTMnet',), verbose: bool=True) -> dict
```

What the atmospheric-correction stack has and lacks, for ``engines``.

Returns a dict with ``isofit`` (version or None), ``ini``, ``base``,
``compilers``, ``assets`` (per ISOFIT key: path, ok, exe) and ``missing``
(human-readable items with the command that supplies each). ``ok`` is
True when nothing is missing. Nothing is downloaded or written.

[Module and aliases](../hyperproc-atmos-setup.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.setup.check --runtime`.
