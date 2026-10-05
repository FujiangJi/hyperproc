# hyperproc.registry.sniff

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def sniff(path: str | Path) -> tuple[str, str] | None
```

Guess ``(sensor, level)`` from a filename. None if nothing matches.

[Module and aliases](../hyperproc-registry.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.registry.sniff --runtime`.
