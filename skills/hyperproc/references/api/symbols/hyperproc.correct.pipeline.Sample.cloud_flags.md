# hyperproc.correct.pipeline.Sample.cloud_flags

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def cloud_flags(self, params: dict) -> np.ndarray
```

Zhai cloud/shadow flag per sampled pixel (True = bad), evaluated in 2-D
on each sampled block with the scene-wide statistics (or, for the
whole-image strategy, taken from the mask computed over the full image).

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.Sample.cloud_flags --runtime`.
