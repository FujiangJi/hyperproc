# hyperproc.atmos.correct.segment_count

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def segment_count(inputs: Inputs) -> int | None
```

How many superpixels a previous run of this work dir actually produced.

ISOFIT's SLIC segmentation writes ``output/<fid>_lbl``; label 0 is the
no-data class, so the count is the maximum label. None when the file is
not there yet.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.segment_count --runtime`.
