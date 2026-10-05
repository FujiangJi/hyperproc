# hyperproc.archive.dlr._time_of

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _time_of(props: dict) -> datetime | None
```

The acquisition time as naive UTC.

STAC writes fractional seconds with however many digits it has;
``fromisoformat`` wants three or six, so they are padded or trimmed first.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr._time_of --runtime`.
