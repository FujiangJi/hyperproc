# hyperproc.correct.mcd43.resolution_of

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def resolution_of(ds) -> float
```

The dataset's ground sample distance, in degrees.

Read from the map grid's own coordinates where there is one (converted
from metres for a projected CRS), otherwise from the spacing of the
per-pixel ``lon``/``lat`` layers of a swath. The larger of the two axes
wins, so the answer is never finer than the image really is.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.resolution_of --runtime`.
