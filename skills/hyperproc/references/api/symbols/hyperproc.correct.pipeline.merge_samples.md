# hyperproc.correct.pipeline.merge_samples

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def merge_samples(samples, stem: str | None=None) -> Sample
```

Pool the samples of several cubes that belong together - the chunks of
one AVIRIS-5 flightline - into one :class:`Sample`, so a topographic C
is fitted per flightline rather than per chunk. Cloud statistics are
recomputed over all pooled blocks.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.merge_samples --runtime`.
