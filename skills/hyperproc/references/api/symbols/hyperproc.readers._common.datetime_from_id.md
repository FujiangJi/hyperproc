# hyperproc.readers._common.datetime_from_id

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def datetime_from_id(granule: str) -> str | None
```

ISO acquisition time encoded in a granule id, or None.

``AV320231005t181518`` -> ``2023-10-05T18:15:18``; ``ang20220224t210144``
likewise; Tanager ``20250503_064345_16_4001`` -> ``2025-05-03T06:43:45``;
AVIRIS Classic ``f201013t01p00r10`` carries the date only.

[Module and aliases](../hyperproc-readers-_common.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers._common.datetime_from_id --runtime`.
