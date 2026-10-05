# hyperproc.archive.neon._months

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _months(date) -> tuple[str, str] | None
```

``date=`` as an inclusive ``("YYYY-MM", "YYYY-MM")`` pair.

A day is accepted and truncated to its month, because a delivery is monthly
and pretending otherwise would drop the flight you asked for.

[Module and aliases](../hyperproc-archive-neon.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.neon._months --runtime`.
