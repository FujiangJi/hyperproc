# hyperproc.archive.interactive.has_cloud

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def has_cloud(sensor: str, level: str | None=None) -> bool
```

Does this collection publish a cloud fraction?

Read from the collection table rather than kept as a second list, because
it is not a property of the sensor: PACE reports one at L2 and none at
L1B. Offering the slider where there is none would silently drop every
granule, which is how a working search looks broken.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.has_cloud --runtime`.
