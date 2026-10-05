# hyperproc.correct.mcd43.available

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def available(date: str, days: int=0, collection: str=COLLECTION, project: str | None=None) -> str
```

The date of the nearest MCD43A1 image within ``days`` of ``date``.

A one-call connectivity and coverage check: it proves Earth Engine is
reachable and that the scene's own date has a granule, without downloading
anything.

Raises:
    RuntimeError: no image in the window (or Earth Engine is unreachable).

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.available --runtime`.
